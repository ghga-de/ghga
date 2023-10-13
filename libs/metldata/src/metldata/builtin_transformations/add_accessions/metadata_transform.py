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

"""Logic for transforming metadata."""

from collections import defaultdict

from pydantic import Json
from typing_extensions import TypeAlias

from metldata.metadata_utils import lookup_self_id
from metldata.model_utils.anchors import AnchorPoint, lookup_anchor_point
from metldata.model_utils.essentials import MetadataModel
from metldata.submission_registry.models import AccessionMap
from metldata.transform.base import MetadataTransformationError

# A type for specifying references between anchored classes in a given model:
# The first key is the name of the class that is anchored, the second key is the
# the name of the slot of that class that contains the references.
# The value is name of the class that is referenced.
References: TypeAlias = dict[str, dict[str, str]]


def get_references(
    *, metadata_model: MetadataModel, anchor_points_by_target: dict[str, AnchorPoint]
) -> References:
    """Get references between anchored classes in a given model."""
    schema_view = metadata_model.schema_view
    references: References = defaultdict(dict)

    for source_class_name in anchor_points_by_target:
        slots = schema_view.class_induced_slots(source_class_name)
        for slot in slots:
            if slot.range in anchor_points_by_target:
                references[source_class_name][slot.name] = slot.range

    return references


def lookup_accession(
    *,
    target_class: str,
    old_identifier: str,
    accession_map: AccessionMap,
    anchor_points_by_target: dict[str, AnchorPoint],
) -> str:
    """Lookup the accession for the a resource with the given identifier of the given
    class.
    """
    anchor_point = lookup_anchor_point(
        class_name=target_class, anchor_points_by_target=anchor_points_by_target
    )
    accession = accession_map.get(anchor_point.root_slot, {}).get(old_identifier)
    if not accession:
        raise MetadataTransformationError(
            f"Could not find accession for '{old_identifier}' of class"
            + f" '{target_class}."
        )
    return accession


def add_accession_to_resource(
    *,
    resource: Json,
    class_name: str,
    old_identifier_slot: str,
    accession_slot_name: str,
    accession_map: AccessionMap,
    references: dict[str, str],
    anchor_points_by_target: dict[str, AnchorPoint],
) -> Json:
    """Add an accession to a resource.

    Args:
        resource:
            The resource to which accessions should be added.
        old_identifier_slot:
            The name of the slot that contains the old identifier.
        old_identifier:
            The old identifier of the resource.
        accession_map:
            The accession map that contains the accessions.
        references:
            References from this to other anchored classes. The keys are the names of
            the slots that contain the references, the values are the names of the
            referenced classes.

    Raises:
        MetadataTransformationError:
            if the transformation of the metadata fails.
    """
    old_identifier = lookup_self_id(
        resource=resource, identifier_slot=old_identifier_slot
    )
    new_identifier = lookup_accession(
        target_class=class_name,
        old_identifier=old_identifier,
        accession_map=accession_map,
        anchor_points_by_target=anchor_points_by_target,
    )

    new_resource: Json = {accession_slot_name: new_identifier}

    for slot_name, slot_value in resource.items():
        if slot_name in references:
            referenced_class = references[slot_name]
            if isinstance(slot_value, list):
                new_resource[slot_name] = [
                    lookup_accession(
                        target_class=referenced_class,
                        old_identifier=reference_old_identifier,
                        accession_map=accession_map,
                        anchor_points_by_target=anchor_points_by_target,
                    )
                    for reference_old_identifier in slot_value
                ]
            else:
                new_resource[slot_name] = lookup_accession(
                    target_class=referenced_class,
                    old_identifier=slot_value,
                    accession_map=accession_map,
                    anchor_points_by_target=anchor_points_by_target,
                )
        else:
            new_resource[slot_name] = slot_value

    return new_resource


def add_accessions_to_metadata(
    *,
    metadata: Json,
    accession_slot_name: str,
    accession_map: AccessionMap,
    references: References,
    anchor_points_by_target: dict[str, AnchorPoint],
) -> Json:
    """Add an accessions to metadata.

    Raises:
        MetadataTransformationError:
            if the transformation of the metadata fails.
    """
    modified_metadata = {}

    for target_class_name, anchor_point in anchor_points_by_target.items():
        target_resources = []
        target_accession_map = accession_map.get(anchor_point.root_slot)
        if target_accession_map is None:
            raise MetadataTransformationError(
                "Could not find accession mapping for target class"
                + f" {target_class_name}."
            )

        for old_resource in metadata[anchor_point.root_slot]:
            new_resource = add_accession_to_resource(
                resource=old_resource,
                class_name=target_class_name,
                old_identifier_slot=anchor_point.identifier_slot,
                accession_slot_name=accession_slot_name,
                accession_map=accession_map,
                references=references[target_class_name],
                anchor_points_by_target=anchor_points_by_target,
            )
            target_resources.append(new_resource)

        modified_metadata[anchor_point.root_slot] = target_resources

    return modified_metadata
