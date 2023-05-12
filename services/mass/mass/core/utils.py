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

"""Utility functions for building the aggregation pipeline used by query handler"""
from collections import defaultdict
from typing import Optional, cast

from hexkit.custom_types import JsonObject

from mass.core import models


def pipeline_match_text_search(*, query: str) -> JsonObject:
    """Build text search segment of aggregation pipeline"""
    text_search = {"$text": {"$search": query}}
    return {"$match": text_search}


def pipeline_match_filters_stage(*, filters: list[models.Filter]) -> JsonObject:
    """Build segment of pipeline to apply search filters"""

    segment: dict[str, dict[str, list[str]]] = defaultdict(lambda: {"$in": []})
    for item in filters:
        filter_key = "content." + str(item.key)
        filter_value = item.value
        segment[filter_key]["$in"].append(filter_value)
    return {"$match": segment}


def build_pipeline(
    *,
    query: str,
    filters: list[models.Filter],
    skip: int = 0,
    limit: Optional[int] = None
) -> list[JsonObject]:
    """Build aggregation pipeline based on query"""
    pipeline: list[JsonObject] = []
    query = query.strip()
    if query:
        pipeline.append(pipeline_match_text_search(query=query))

    pipeline.append({"$sort": {"_id": 1}})

    if filters:
        pipeline.append(pipeline_match_filters_stage(filters=filters))

    pipeline.append({"$skip": skip})
    if limit:
        pipeline.append({"$limit": limit})

    return pipeline


def document_to_resource(*, document: JsonObject) -> models.Resource:
    """Convert a document to a pydantic model"""
    id_ = str(document["_id"])
    content = cast(JsonObject, document["content"])
    return models.Resource(id_=id_, content=content)
