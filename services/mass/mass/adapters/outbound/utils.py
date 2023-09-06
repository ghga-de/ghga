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
from typing import Any, Optional

from hexkit.custom_types import JsonObject

from mass.core import models

SORT_ORDER_CONVERSION = {"ascending": 1, "descending": -1}


def pipeline_match_text_search(*, query: str) -> JsonObject:
    """Build text search segment of aggregation pipeline"""
    text_search = {"$text": {"$search": query}}
    return {"$match": text_search}


def args_for_getfield(*, root_object_name: str, field_name: str) -> tuple[str, str]:
    """fieldpath names can't have '.', so specify any nested fields with $getField"""
    prefix = f"${root_object_name}"
    specified_field = field_name
    if "." in field_name:
        pieces = field_name.split(".")
        specified_field = pieces[-1]
        prefix += "." + ".".join(pieces[:-1])

    return (prefix, specified_field)


def pipeline_match_filters_stage(*, filters: list[models.Filter]) -> JsonObject:
    """Build segment of pipeline to apply search filters"""

    segment: dict[str, dict[str, list[str]]] = defaultdict(lambda: {"$in": []})
    for item in filters:
        filter_key = "content." + str(item.key)
        filter_value = item.value
        segment[filter_key]["$in"].append(filter_value)

    return {"$match": segment}


def pipeline_facet_sort_and_paginate(
    *,
    facet_fields: list[models.FacetLabel],
    skip: int,
    limit: Optional[int] = None,
    sorts: JsonObject,
):
    """Uses a list of facetable property names to build the subquery for faceting"""
    segment: dict[str, list[JsonObject]] = {}

    for facet in facet_fields:
        prefix, specified_field = args_for_getfield(
            root_object_name="content", field_name=facet.key
        )

        segment[facet.name] = [
            {
                "$group": {
                    "_id": {"$getField": {"field": specified_field, "input": prefix}},
                    "count": {"$sum": 1},
                }
            },
            {"$addFields": {"value": "$_id"}},  # rename "_id" to "value" on each option
            {"$unset": "_id"},
        ]

    # this is the total number of hits, but pagination can mean only a few are returned
    segment["count"] = [{"$count": "total"}]

    # sort by ID, then rename the ID field to id_ to match our model
    segment["hits"] = [
        {"$addFields": {"id_": "$_id"}},
        {"$unset": "_id"},
        {"$sort": sorts},
    ]

    # apply skip and limit for pagination
    if skip > 0:
        segment["hits"].append({"$skip": skip})

    if limit:
        segment["hits"].append({"$limit": limit})

    return {"$facet": segment}


def pipeline_project(*, facet_fields: list[models.FacetLabel]) -> JsonObject:
    """Reshape the query so the facets are contained in a top level object"""
    segment: dict[str, Any] = {"hits": 1, "facets": []}
    segment["count"] = {"$arrayElemAt": ["$count.total", 0]}

    # add a segment for each facet to summarize the options
    for facet in facet_fields:
        segment["facets"].append(
            {"key": facet.key, "name": facet.name, "options": f"${facet.name}"}
        )
    return {"$project": segment}


def build_pipeline(
    *,
    query: str,
    filters: list[models.Filter],
    facet_fields: list[models.FacetLabel],
    skip: int = 0,
    limit: Optional[int] = None,
    sorting_parameters: list[models.SortingParameter],
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

    # turn the sorting parameters into a formatted pipeline $sort
    sorts = {}
    for param in sorting_parameters:
        sort_order = SORT_ORDER_CONVERSION[param.order.value]
        sorts[param.field] = sort_order

    # define facets from preliminary results and reshape data
    pipeline.append(
        pipeline_facet_sort_and_paginate(
            facet_fields=facet_fields,
            skip=skip,
            limit=limit,
            sorts=sorts,
        )
    )

    # transform data one more time to match models
    pipeline.append(pipeline_project(facet_fields=facet_fields))

    return pipeline
