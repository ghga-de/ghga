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

"""Logic for handling information on artifacts."""

import json
from typing import Optional

from linkml.generators.jsonschemagen import JsonSchemaGenerator
from linkml_runtime.linkml_model.annotations import Annotation
from linkml_runtime.linkml_model.meta import ClassDefinition, ClassDefinitionName

from metldata.artifacts_rest.models import ArtifactInfo, ArtifactResourceClass
from metldata.custom_types import Json
from metldata.model_utils.anchors import (
    get_anchors_points_by_target,
    lookup_anchor_point,
)
from metldata.model_utils.assumptions import check_basic_model_assumption
from metldata.model_utils.essentials import MetadataModel


def is_class_hidden(*, class_definition: ClassDefinition) -> bool:
    """Check if a metadata class is annotated as `hidden`."""

    if not isinstance(class_definition.annotations, dict):
        raise RuntimeError(  # This should never happen
            f"Annotations of class {class_definition.name} are not a dictionary."
        )

    if "hidden" in class_definition.annotations:
        if not isinstance(class_definition.annotations["hidden"], Annotation):
            raise RuntimeError(  # This should never happen
                f"Annotation 'hidden' of class {class_definition.name} has an"
                + " unexpected format."
            )

        if not isinstance(class_definition.annotations["hidden"].value, bool):
            raise RuntimeError(  # This should never happen
                f"Annotation 'hidden' of class {class_definition.name} has an"
                + " unexpected value."
            )

        return class_definition.annotations["hidden"].value

    return False


def get_resource_class_names(*, model: MetadataModel) -> list[str]:
    """Get the names of all classes from a metadata model.
    Only anchored classes are considered. Classes that are annotated as `hidden`
    are ignored.
    """

    anchored_class_names = get_anchors_points_by_target(model=model).keys()
    schema_view = model.schema_view

    return [
        anchored_class_name
        for anchored_class_name in anchored_class_names
        if not is_class_hidden(
            class_definition=schema_view.get_class(anchored_class_name, strict=True)
        )
    ]


def load_json_schema_for_class(*, model: MetadataModel, class_name: str) -> Json:
    """Load the JSON schema for the specified class of the metadata model."""

    return json.loads(
        JsonSchemaGenerator(
            model, top_class=ClassDefinitionName(class_name)
        ).serialize()
    )


def load_description_for_class(
    *, model: MetadataModel, class_name: str
) -> Optional[str]:
    """Load the description for the specified class of the metadata model."""

    return model.schema_view.get_class(class_name, strict=True).description


def load_resource_classes(*, model: MetadataModel) -> dict[str, ArtifactResourceClass]:
    """Load all classes from a metadata model.
    Only anchored classes are considered. Classes that are annotated as `hidden`
    are ignored.

    Args:
        model: The metadata model.

    Returns:
        A dictionary of resource classes for this artifact.
        The keys are the names of the metadata classes. The values are the
        corresponding metadata class models.
    """

    anchor_points_by_target = get_anchors_points_by_target(model=model)

    resource_class_names = get_resource_class_names(model=model)

    return {
        resource_class_name: ArtifactResourceClass(
            name=resource_class_name,
            description=load_description_for_class(
                model=model, class_name=resource_class_name
            ),
            anchor_point=lookup_anchor_point(
                class_name=resource_class_name,
                anchor_points_by_target=anchor_points_by_target,
            ),
            json_schema=load_json_schema_for_class(
                model=model, class_name=resource_class_name
            ),
        )
        for resource_class_name in resource_class_names
    }


def load_artifact_info(
    *, name: str, description: str, model: MetadataModel
) -> ArtifactInfo:
    """Load artifact info from a metadata model.

    Args:
        name: The name of the artifact.
        description: A description of the artifact.
        model: The metadata model for the artifact.

    Returns:
        The artifact info model.
    """

    check_basic_model_assumption(model)

    resource_classes = load_resource_classes(model=model)

    return ArtifactInfo(
        name=name,
        description=description,
        resource_classes=resource_classes,
    )


def get_artifact_info_dict(
    *, artifact_infos: list[ArtifactInfo]
) -> dict[str, ArtifactInfo]:
    """Build a dictionary from artifact name to artifact info."""

    # check if artifact names are unique:
    artifact_names = [artifact_info.name for artifact_info in artifact_infos]
    if len(artifact_names) != len(set(artifact_names)):
        raise ValueError("Artifact names must be unique.")

    return {artifact_info.name: artifact_info for artifact_info in artifact_infos}
