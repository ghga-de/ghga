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

"""Logic for handling identifiers and accessions."""

from collections.abc import Iterable
from functools import partial
from typing import Optional
from uuid import uuid4

from pydantic import Json

from metldata.accession_registry import AccessionRegistry
from metldata.custom_types import SubmissionContent
from metldata.metadata_utils import lookup_self_id
from metldata.model_utils.anchors import (
    AnchorPoint,
    invert_anchor_points_by_target,
    lookup_anchor_point,
    lookup_class_by_anchor_point,
)
from metldata.submission_registry.models import AccessionMap


def generate_submission_id() -> str:
    """Generate a new submission ID."""
    return str(uuid4())


def lookup_accession(
    *,
    anchor: str,
    alias: str,
    accession_map: AccessionMap,
) -> Optional[str]:
    """Lookup the accession for a resource with the provided user-defined alias of
    the class with the provided anchor. If no accession exists, None is returned.
    """
    return accession_map.get(anchor, {}).get(alias, None)


def get_accession(
    *,
    anchor: str,
    alias: str,
    accession_map: AccessionMap,
    accession_registry: AccessionRegistry,
    target_by_anchor_point: dict[str, str],
) -> str:
    """Get the accession for a resource with the provided user-defined alias of
    the class with the provided anchor. If no entry can be found in the provided accession map,
    a new accession is requested from the provided accession registry.
    """
    accession = lookup_accession(
        anchor=anchor, alias=alias, accession_map=accession_map
    )
    if accession:
        return accession

    class_name = lookup_class_by_anchor_point(
        root_slot=anchor, target_by_anchor_point=target_by_anchor_point
    )
    return accession_registry.get_accession(resource_type=class_name)


def get_aliases_for_resources(
    *,
    resources: list[Json],
    root_slot: str,
    anchor_points_by_target: dict[str, AnchorPoint],
) -> Iterable[str]:
    """Get the aliases for the provided resources."""
    target_by_anchor_point = invert_anchor_points_by_target(
        anchor_points_by_target=anchor_points_by_target
    )

    class_name = lookup_class_by_anchor_point(
        root_slot=root_slot, target_by_anchor_point=target_by_anchor_point
    )
    anchor_point = lookup_anchor_point(
        class_name=class_name, anchor_points_by_target=anchor_points_by_target
    )

    for resource in resources:
        yield lookup_self_id(
            resource=resource, identifier_slot=anchor_point.identifier_slot
        )


def generate_accession_map(
    *,
    content: SubmissionContent,
    existing_accession_map: Optional[AccessionMap] = None,
    accession_registry: AccessionRegistry,
    anchor_points_by_target: dict[str, AnchorPoint],
) -> AccessionMap:
    """Generate an accession map for the provided content.

    If an existing accession map is provided, an updated version is returned. Thereby,
    new accessions are added for new content resources. Existing accessions are kept if
    the corresponding content resource still exists, otherwise they are removed.
    """
    if existing_accession_map is None:
        existing_accession_map = {}

    target_by_anchor_point = invert_anchor_points_by_target(
        anchor_points_by_target=anchor_points_by_target
    )

    get_accession_ = partial(
        get_accession,
        accession_map=existing_accession_map,
        accession_registry=accession_registry,
        target_by_anchor_point=target_by_anchor_point,
    )

    return {
        anchor: {
            alias: get_accession_(anchor=anchor, alias=alias)
            for alias in get_aliases_for_resources(
                resources=resources,
                root_slot=anchor,
                anchor_points_by_target=anchor_points_by_target,
            )
        }
        for anchor, resources in content.items()
    }
