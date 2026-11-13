# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""MongoDB adapter for getting the files that wait for interrogation."""

from pymongo import AsyncMongoClient

from fis.constants import BOX_PRIORITY_EVENT_KEY
from fis.core.models import BaseFileInformation
from fis.ports.outbound.interrogation_queue import InterrogationQueuePort


class MongoDbInterrogationQueue(InterrogationQueuePort):
    """Ranks the waiting files with a server-side MongoDB aggregation.

    This bypasses the hexkit DAO deliberately: the DAO would load and validate every
    waiting file, only for FIS to rank them and drop all but a few. MongoDB combines
    the `$sort` with the `$limit` and keeps only the top files in memory.
    """

    def __init__(
        self,
        *,
        client: AsyncMongoClient,
        db_name: str,
        files_collection_name: str,
        priority_collection_name: str,
    ):
        self._collection = client[db_name][files_collection_name]
        self._priority_collection_name = priority_collection_name

    async def get_waiting_files(
        self, *, storage_alias: str, limit: int
    ) -> list[BaseFileInformation]:
        """Return up to `limit` files of the storage alias that wait for interrogation.

        Files of boxes in the upload box priority list come first, in list order.
        Files of the same box, and files without a listed box, come in `id` order.
        """
        pipeline: list[dict] = [
            {
                "$match": {
                    "storage_alias": storage_alias,
                    "state": "inbox",
                    "interrogated": False,
                }
            },
            # Doesn't depend on the file, so MongoDB runs it once per query
            {
                "$lookup": {
                    "from": self._priority_collection_name,
                    "pipeline": [
                        {"$match": {"_id": BOX_PRIORITY_EVENT_KEY}},
                        {"$project": {"_id": 0, "entries": 1}},
                    ],
                    "as": "priority",
                }
            },
            # -1 if the box isn't listed, there is no list, or the file has no box
            {
                "$set": {
                    "rank": {
                        "$indexOfArray": [
                            {"$ifNull": [{"$first": "$priority.entries.box_id"}, []]},
                            "$box_id",
                        ]
                    }
                }
            },
            {"$set": {"unprioritized": {"$eq": ["$rank", -1]}}},
            {"$sort": {"unprioritized": 1, "rank": 1, "_id": 1}},
            {"$limit": limit},
            {"$project": {"priority": 0, "rank": 0, "unprioritized": 0}},
        ]
        cursor = await self._collection.aggregate(pipeline)
        files: list[BaseFileInformation] = []
        async for document in cursor:
            document["id"] = document.pop("_id")
            files.append(BaseFileInformation.model_validate(document))
        return files
