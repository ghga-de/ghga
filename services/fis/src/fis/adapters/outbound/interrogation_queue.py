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

from typing import Any

from pymongo import AsyncMongoClient

from fis.constants import BOX_PRIORITY_EVENT_KEY
from fis.core.models import BaseFileInformation, FileUnderInterrogation
from fis.ports.outbound.interrogation_queue import InterrogationQueuePort
from ghga_service_commons.utils.utc_dates import UTCDatetime


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
        ranked_documents = await self._rank(
            match={
                "storage_alias": storage_alias,
                "state": "inbox",
                "interrogated": False,
            },
            sort={"_id": 1},
            limit=limit,
        )
        return [
            BaseFileInformation.model_validate(document)
            for _, document in ranked_documents
        ]

    async def get_claimable_files(
        self, *, storage_alias: str, claim_time: UTCDatetime, limit: int
    ) -> list[FileUnderInterrogation]:
        """Return up to `limit` waiting and not leased files for the specified storage
        alias. All of them come from the highest-priority box that has a claimable
        file.

        Boxes go by the upload box priority list. Within the box, files not yet claimed
        come first. Then come files whose lease ran out, earliest first. Ties go by
        `state_updated`.

        If for any reason a file can't be ranked (problem with the prio list, or
        box ID is missing, etc.), it gets lumped into a placeholder box with lowest
        priority.
        """
        ranked_documents = await self._rank(
            match={
                "storage_alias": storage_alias,
                "state": "inbox",
                "interrogated": False,
                "$or": [{"leased_until": None}, {"leased_until": {"$lt": claim_time}}],
            },
            # Null sorts before any date, so never-claimed files come first
            sort={"leased_until": 1, "state_updated": 1, "_id": 1},
            limit=limit,
        )
        # Drop lower-ranked files, so that a random pick can't skip a higher-ranked box
        return [
            FileUnderInterrogation.model_validate(document)
            for rank, document in ranked_documents
            if rank == ranked_documents[0][0]
        ]

    async def _rank(
        self, *, match: dict[str, Any], sort: dict[str, int], limit: int
    ) -> list[tuple[int, dict[str, Any]]]:
        """Return up to `limit` matching documents, ranked by the priority list first
        and by `sort` within a rank, with `_id` renamed to `id`.

        Each document returned contains a `rank` field, which is its box's index in
        the priority list, or -1 if the box isn't listed (an edge case).
        """
        pipeline: list[dict] = [
            {"$match": match},
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
            {"$sort": {"unprioritized": 1, "rank": 1, **sort}},
            {"$limit": limit},
            {"$project": {"priority": 0, "unprioritized": 0}},
        ]
        cursor = await self._collection.aggregate(pipeline)
        documents: list[tuple[int, dict[str, Any]]] = []
        async for document in cursor:
            document["id"] = document.pop("_id")
            documents.append((document.pop("rank"), document))
        return documents
