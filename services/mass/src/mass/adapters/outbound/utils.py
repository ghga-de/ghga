# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
from typing import Any

from hexkit.custom_types import JsonObject

from mass.core import models

SORT_ORDER_CONVERSION: JsonObject = {
    "ascending": 1,
    "descending": -1,
    "relevance": {"$meta": "textScore"},
}


def name_from_key(key: str) -> str:
    """Auto generate a suitable name from a key"""
    return key.title().replace("_", " ").replace(".", " ")


def pipeline_match_text_search(*, query: str) -> JsonObject:
    """Build text search segment of aggregation pipeline"""
    text_search = {"$text": {"$search": query}}
    return {"$match": text_search}


def pipeline_match_filters_stage(*, filters: list[models.Filter]) -> JsonObject:
    """Build segment of pipeline to apply search filters"""
    filter_values = defaultdict(list)
    for item in filters:
        filter_values[item.key].append(item.value)
    segment = []
    for key, values in filter_values.items():
        if key != "id_":
            key = "content." + key
        segment.append(
            {
                "$or": [
                    {
                        "$and": [
                            {key: {"$not": {"$type": "array"}}},
                            {key: {"$in": values}},
                        ]
                    },
                    {
                        "$and": [
                            {key: {"$type": "array"}},
                            {key: {"$elemMatch": {"$in": values}}},
                        ]
                    },
                ]
            }
        )
    return {"$match": {"$and": segment}}


def pipeline_facet_sort_and_paginate(
    *,
    facet_fields: list[models.FieldLabel],
    skip: int = 0,
    limit: int | None = None,
    project: dict[str, Any] | None = None,
    sort: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Uses a list of facetable fields to build the subquery for faceting"""
    segment: dict[str, list[JsonObject]] = {}

    for facet in facet_fields:
        name = facet.name
        if not name:
            name = name_from_key(facet.key)
        pipeline: list[JsonObject] = [
            {
                "$unwind": {
                    "path": "$content",
                    "preserveNullAndEmptyArrays": True,
                }
            },
        ]
        path = "$content"
        for field in facet.key.split("."):
            path += f".{field}"
            pipeline.append(
                {
                    "$unwind": {
                        "path": path,
                        "preserveNullAndEmptyArrays": True,
                    }
                },
            )
        path, field = path.rsplit(".", 1)
        pipeline.extend(
            (
                {
                    "$group": {
                        "_id": {"$getField": {"field": field, "input": path}},
                        "uniqueIds": {"$addToSet": "$_id"},
                    }
                },
                {"$match": {"_id": {"$ne": None}}},
                {"$addFields": {"value": "$_id", "count": {"$size": "$uniqueIds"}}},
                {"$unset": "_id"},
                {"$sort": {"value": 1}},
            )
        )
        segment[name] = pipeline

    # this is the total number of hits, but pagination can mean only a few are returned
    segment["count"] = [{"$count": "total"}]

    # rename the ID field to id_ to match our model
    segment["hits"] = [{"$addFields": {"id_": "$_id"}}, {"$unset": "_id"}]

    # apply sorting parameters (maybe some of them are unselected fields)
    if sort:
        segment["hits"].append({"$sort": sort})

    # pick only the selected fields
    if project:
        segment["hits"].append({"$project": project})

    # apply skip and limit for pagination
    if skip > 0:
        segment["hits"].append({"$skip": skip})
    if limit:
        segment["hits"].append({"$limit": limit})

    return {"$facet": segment}


def pipeline_project(*, facet_fields: list[models.FieldLabel]) -> JsonObject:
    """Reshape the query so the facets are contained in a top level object"""
    segment: dict[str, Any] = {"hits": 1, "facets": []}
    segment["count"] = {"$arrayElemAt": ["$count.total", 0]}

    # add a segment for each facet to summarize the options
    for facet in facet_fields:
        key = facet.key
        name = facet.name
        if not name:
            name = name_from_key(key)
        segment["facets"].append(
            {
                "key": key,
                "name": name,
                "options": f"${name}",
            }
        )
    return {"$project": segment}


def build_pipeline(  # noqa: PLR0913
    *,
    facet_fields: list[models.FieldLabel],
    selected_fields: list[models.FieldLabel],
    query: str,
    filters: list[models.Filter],
    sorting_parameters: list[models.SortingParameter],
    skip: int = 0,
    limit: int | None = None,
) -> list[JsonObject]:
    """Build aggregation pipeline based on query"""
    pipeline: list[JsonObject] = []
    query = query.strip()

    # perform text search
    if query:
        pipeline.append(pipeline_match_text_search(query=query))

    # apply filters
    if filters:
        pipeline.append(pipeline_match_filters_stage(filters=filters))

    # turn the selected fields into a formatted pipeline $project

    project: dict[str, int] | None = (
        dict.fromkeys(
            (
                "id_",
                *(
                    f"content.{field.key}"
                    for field in selected_fields
                    if field.key != "id_"
                ),
            ),
            1,
        )
        if selected_fields
        else None
    )

    # turn the sorting parameters into a formatted pipeline $sort
    sort: dict[str, Any] = {
        param.field
        if param.field == "id_"
        else f"content.{param.field}": SORT_ORDER_CONVERSION[param.order.value]
        for param in sorting_parameters
    }

    # define facets from preliminary results and reshape data
    pipeline.append(
        pipeline_facet_sort_and_paginate(
            facet_fields=facet_fields,
            skip=skip,
            limit=limit,
            project=project,
            sort=sort,
        )
    )

    # transform data one more time to match models
    pipeline.append(pipeline_project(facet_fields=facet_fields))

    return pipeline
