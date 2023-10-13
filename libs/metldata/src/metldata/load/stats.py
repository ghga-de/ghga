# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
#

"""Generate global summary statistics."""

from operator import itemgetter
from typing import Any, Optional, cast

from ghga_service_commons.utils.utc_dates import now_as_utc

from metldata.artifacts_rest.models import (
    ArtifactInfo,
    GlobalStats,
    ResourceStats,
    ValueCount,
)
from metldata.load.aggregator import DbAggregator

STATS_COLLECTION_NAME = "stats"


def get_stat_slot(resource_class: str) -> Optional[str]:
    """Get the name of the slot that shall be used as grouping key."""
    if resource_class.endswith("File"):
        return "format"
    if resource_class.endswith("Protocol"):
        return "type"
    if resource_class.endswith("Individual"):
        return "sex"
    return None


async def create_stats_using_aggregator(
    artifact_infos: dict[str, ArtifactInfo],
    primary_artifact_name: str,
    db_aggregator: DbAggregator,
) -> None:
    """Create summary by running an aggregation pipeline on the database."""
    resource_stats: dict[str, ResourceStats] = {}
    artifact_name = primary_artifact_name
    artifact_info = artifact_infos[artifact_name]
    for resource_class in artifact_info.resource_classes:
        collection_name = f"art_{artifact_name}_class_{resource_class}"

        pipeline: list[dict[str, Any]] = [{"$count": "count"}]
        result = await db_aggregator.aggregate(
            collection_name=collection_name, pipeline=pipeline
        )
        if not result:
            continue
        resource_stats[resource_class] = cast(ResourceStats, result[0])

        stat_slot = get_stat_slot(resource_class)
        if not stat_slot:
            continue

        pipeline = [{"$group": {"_id": f"$content.{stat_slot}", "count": {"$sum": 1}}}]
        result = await db_aggregator.aggregate(
            collection_name=collection_name, pipeline=pipeline
        )
        if not result:
            continue

        stats: list[ValueCount] = sorted(
            (
                {"value": group["_id"] or "unknown", "count": group["count"]}
                for group in result
            ),
            key=itemgetter("value"),
        )
        resource_stats[resource_class]["stats"] = {stat_slot: stats}

    if resource_stats:
        global_stats = GlobalStats(
            id="global", created=now_as_utc(), resource_stats=resource_stats
        )
        stats_dao = await db_aggregator.get_dao(
            name=STATS_COLLECTION_NAME, dto_model=GlobalStats, id_field="id"
        )
        await stats_dao.upsert(global_stats)
