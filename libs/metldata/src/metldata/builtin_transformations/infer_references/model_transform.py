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

"""Logic for transforming metadata models."""

from linkml_runtime.linkml_model.meta import SlotDefinition

from metldata.builtin_transformations.infer_references.reference import (
    InferredReference,
)
from metldata.model_utils.essentials import MetadataModel
from metldata.model_utils.manipulate import (
    ModelManipulationError,
    add_slot_if_not_exists,
    upsert_class_slot,
)
from metldata.transform.base import MetadataModelTransformationError


def inferred_reference_to_slot(reference: InferredReference) -> SlotDefinition:
    """Convert an inferred reference into a slot definition to be mounted on the
    source class.
    """
    return SlotDefinition(
        name=reference.new_slot,
        range=reference.target,
        multivalued=reference.multivalued,
        inlined=False,
        required=True,
    )


def add_reference_to_model(
    *, model: MetadataModel, reference: InferredReference
) -> MetadataModel:
    """Get a modified copy of the provided model with the inferred reference being
    added.

    Raises:
            MetadataModelTransformationError:
                if the transformation of the metadata model fails.
    """
    new_slot = inferred_reference_to_slot(reference)

    schema_view = model.schema_view
    try:
        schema_view = add_slot_if_not_exists(schema_view=schema_view, new_slot=new_slot)
        schema_view = upsert_class_slot(
            schema_view=schema_view, class_name=reference.source, new_slot=new_slot
        )
    except ModelManipulationError as error:
        raise MetadataModelTransformationError(
            f"Failed to add the inferred reference '{reference}' to the metadata"
            + f" model.: {error}"
        ) from error

    return schema_view.export_model()


def add_references_to_model(
    *, model: MetadataModel, references: list[InferredReference]
) -> MetadataModel:
    """Transform the metadata model and return the transformed one.
    Raises:
            MetadataModelTransformationError:
                if the transformation of the metadata model fails.
    """
    for reference in references:
        model = add_reference_to_model(model=model, reference=reference)

    return model
