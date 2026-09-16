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

"""MongoDB adapter for aggregating FileUploadBox statistics."""

from pydantic import UUID4
from pymongo import AsyncMongoClient

from ucs.constants import COUNTED_UPLOAD_STATES
from ucs.ports.outbound.dao import BoxStatsAggregatorPort


class MongoDbBoxStatsAggregator(BoxStatsAggregatorPort):
    """Computes box stats with a server-side MongoDB aggregation.

    This bypasses the hexkit DAO deliberately: the DAO would deserialize each matching
    FileUpload document (including its large per-part checksum lists) into a Pydantic
    model just to read `decrypted_size`. The aggregation instead sums the values inside
    MongoDB and returns only the two resulting numbers.
    """

    def __init__(self, *, client: AsyncMongoClient, db_name: str, collection_name: str):
        self._collection = client[db_name][collection_name]

    async def compute_box_stats(self, *, box_id: UUID4) -> tuple[int, int]:
        """Return `(file_count, total_decrypted_size)` for the counted FileUploads in
        the box. Returns `(0, 0)` when the box has no counted files.
        """
        pipeline: list[dict] = [
            {
                "$match": {
                    "box_id": box_id,
                    "state": {"$in": list(COUNTED_UPLOAD_STATES)},
                }
            },
            {
                "$group": {
                    "_id": None,
                    "file_count": {"$sum": 1},
                    "size": {"$sum": "$decrypted_size"},
                }
            },
        ]
        cursor = await self._collection.aggregate(pipeline)
        async for group in cursor:
            return group["file_count"], group["size"]
        return 0, 0
