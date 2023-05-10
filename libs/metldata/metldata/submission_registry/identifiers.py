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

from functools import partial
from typing import Any, Optional
from uuid import uuid4

from metldata.accession_registry import AccessionRegistry
from metldata.model_utils.anchors import lookup_class_by_anchor_point


def generate_submission_id() -> str:
    """Generate a new submission ID."""

    return str(uuid4())


def lookup_accession(
    *,
    anchor: str,
    alias: str,
    accession_map: dict[str, dict[str, str]],
) -> Optional[str]:
    """Lookup the accession for a resource with the provided user-defined alias of
    the class with the provided anchor. If no accession exists, None is returned."""

    return accession_map.get(anchor, {}).get(alias, None)


def get_accession(
    *,
    anchor: str,
    alias: str,
    accession_map: dict[str, dict[str, str]],
    accession_registry: AccessionRegistry,
    classes_by_anchor_point: dict[str, str],
) -> str:
    """Get the accession for a resource with the provided user-defined alias of
    the class with the provided anchor. If no entry can be found in the provided accession map,
    a new accession is requested from the provided accession registry."""

    accession = lookup_accession(
        anchor=anchor, alias=alias, accession_map=accession_map
    )
    if accession:
        return accession

    class_name = lookup_class_by_anchor_point(
        root_slot=anchor, classes_by_anchor_point=classes_by_anchor_point
    )
    return accession_registry.get_accession(resource_type=class_name)


def generate_accession_map(
    *,
    content: dict[str, dict[str, Any]],
    existing_accession_map: Optional[dict[str, dict[str, str]]] = None,
    accession_registry: AccessionRegistry,
    classes_by_anchor_point: dict[str, str],
) -> dict[str, dict[str, str]]:
    """Generate an accession map for the provided content.

    If an existing accession map is provided, an updated version is returned. Thereby,
    new accessions are added for new content resources. Existing accessions are kept if
    the corresponding content resource still exists, otherwise they are removed."""

    if existing_accession_map is None:
        existing_accession_map = {}

    get_accession_ = partial(
        get_accession,
        accession_map=existing_accession_map,
        accession_registry=accession_registry,
        classes_by_anchor_point=classes_by_anchor_point,
    )

    return {
        anchor: {
            alias: get_accession_(anchor=anchor, alias=alias) for alias in resources
        }
        for anchor, resources in content.items()
    }
