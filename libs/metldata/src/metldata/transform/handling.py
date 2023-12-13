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

"""Logic for handling Transformation."""

from pydantic import BaseModel, ConfigDict

from metldata.custom_types import Json
from metldata.event_handling.models import SubmissionAnnotation
from metldata.model_utils.essentials import MetadataModel
from metldata.model_utils.metadata_validator import MetadataValidator
from metldata.transform.base import (
    Config,
    TransformationDefinition,
    WorkflowConfig,
    WorkflowDefinition,
    WorkflowStep,
    WorkflowStepBase,
)


class WorkflowConfigMismatchError(RuntimeError):
    """Raised when the provided workflow config does not match the config class of the
    workflow definition.
    """

    def __init__(
        self, workflow_definition: WorkflowDefinition, workflow_config: Config
    ):
        """Initialize the error with the workflow definition and the config."""
        message = (
            f"The config {workflow_config} is not an instance of the config class "
            f"{workflow_definition.config_cls} of the workflow definition "
            f"{workflow_definition}."
        )
        super().__init__(message)


class TransformationHandler:
    """Used for executing transformations described in a TransformationDefinition."""

    def __init__(
        self,
        transformation_definition: TransformationDefinition[Config],
        transformation_config: Config,
        original_model: MetadataModel,
    ):
        """Initialize the TransformationHandler by checking the assumptions made on the
        original model and transforming the model as described in the transformation
        definition. The transformed model is available at the `transformed_model`
        attribute.

        Raises:
            ModelAssumptionError:
                if the assumptions made on the original model are not met.
        """
        self._definition = transformation_definition
        self._config = transformation_config
        self._original_model = original_model

        self._definition.check_model_assumptions(self._original_model, self._config)
        self.transformed_model = self._definition.transform_model(
            self._original_model, self._config
        )
        self._metadata_transformer = self._definition.metadata_transformer_factory(
            config=self._config,
            original_model=self._original_model,
            transformed_model=self.transformed_model,
        )

        self._original_metadata_validator = MetadataValidator(
            model=self._original_model
        )
        self._transformed_metadata_validator = MetadataValidator(
            model=self.transformed_model
        )

    def transform_metadata(
        self,
        metadata: Json,
        *,
        annotation: SubmissionAnnotation,
        assume_validated: bool = False,
    ) -> Json:
        """Transforms metadata using the transformation definition. Validates the
        original metadata against the original model and the transformed metadata
        against the transformed model.

        Args:
            metadata: The metadata to be transformed.
            annotation: The annotation on the metadata.
            assume_validated: Whether the input can be assumed to be valid.

        Raises:
            MetadataTransformationError:
                if the transformation fails.
        """
        if not assume_validated:
            self._original_metadata_validator.validate(metadata)
        transformed_metadata = self._metadata_transformer.transform(
            metadata=metadata, annotation=annotation
        )
        self._transformed_metadata_validator.validate(transformed_metadata)

        return transformed_metadata


class ResolvedWorkflowStep(WorkflowStepBase):
    """A resolved workflow step contains a transformation handler."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    transformation_handler: TransformationHandler


class ResolvedWorkflow(WorkflowDefinition):
    """A resolved workflow contains a list of resolved workflow steps."""

    steps: dict[str, ResolvedWorkflowStep]  # type: ignore
    workflow_config: WorkflowConfig


def check_workflow_config(
    *, workflow_definition: WorkflowDefinition, workflow_config: WorkflowConfig
):
    """Checks if the config is an instance of the config class of the workflow
    definition.

    Raises:
        WorkflowConfigMismatchError:
    """
    if isinstance(workflow_config, workflow_definition.config_cls):
        raise WorkflowConfigMismatchError(
            workflow_definition=workflow_definition, workflow_config=workflow_config
        )


def resolve_workflow_step(
    *,
    workflow_step: WorkflowStep,
    step_name: str,
    workflow_definition: WorkflowDefinition,
    workflow_config: WorkflowConfig,
    original_model: MetadataModel,
) -> ResolvedWorkflowStep:
    """Translates a workflow step given a workflow definition and a workflow config
    into a resolved workflow step.
    """
    check_workflow_config(
        workflow_definition=workflow_definition, workflow_config=workflow_config
    )

    transformation_config: BaseModel = getattr(workflow_config, step_name)
    transformation_handler = TransformationHandler(
        transformation_definition=workflow_step.transformation_definition,
        transformation_config=transformation_config,
        original_model=original_model,
    )
    return ResolvedWorkflowStep(
        transformation_handler=transformation_handler,
        input=workflow_step.input,
        description=workflow_step.description,
    )


def resolve_workflow(
    workflow_definition: WorkflowDefinition,
    original_model: MetadataModel,
    workflow_config: WorkflowConfig,
) -> ResolvedWorkflow:
    """Translates a workflow definition given an input model and a workflow config into
    a resolved workflow.
    """
    check_workflow_config(
        workflow_definition=workflow_definition, workflow_config=workflow_config
    )

    resolved_steps: dict[str, ResolvedWorkflowStep] = {}
    for step_name in workflow_definition.step_order:
        workflow_step = workflow_definition.steps[step_name]
        input_model = (
            original_model
            if workflow_step.input is None
            else resolved_steps[
                workflow_step.input
            ].transformation_handler.transformed_model
        )

        resolved_steps[step_name] = resolve_workflow_step(
            workflow_step=workflow_step,
            step_name=step_name,
            workflow_definition=workflow_definition,
            workflow_config=workflow_config,
            original_model=input_model,
        )

    return ResolvedWorkflow(
        steps=resolved_steps,
        workflow_config=workflow_config,
        description=workflow_definition.description,
        artifacts=workflow_definition.artifacts,
    )


def get_model_artifacts_from_resolved_workflow(resolved_workflow: ResolvedWorkflow):
    """Returns a dictionary of models for artifacts produced by resolved workflow."""
    return {
        artifact_name: resolved_workflow.steps[
            step_name
        ].transformation_handler.transformed_model
        for artifact_name, step_name in resolved_workflow.artifacts.items()
    }


class WorkflowHandler:
    """Used for executing workflows described in a WorkflowDefinition."""

    def __init__(
        self,
        workflow_definition: WorkflowDefinition,
        workflow_config: WorkflowConfig,
        original_model: MetadataModel,
    ):
        """Initialize the WorkflowHandler with a workflow deinition, a matching
        config, and a metadata model. The workflow definition is translated into a
        resolved workflow.
        """
        self._resolved_workflow = resolve_workflow(
            workflow_definition=workflow_definition,
            original_model=original_model,
            workflow_config=workflow_config,
        )

        self.artifact_models = get_model_artifacts_from_resolved_workflow(
            self._resolved_workflow
        )

    def run(
        self, *, metadata: Json, annotation: SubmissionAnnotation
    ) -> dict[str, Json]:
        """Run the workflow definition on metadata and its annotation to generate
        artifacts.
        """
        transformed_metadata: dict[str, Json] = {}
        assume_validated = False
        for step_name in self._resolved_workflow.step_order:
            step = self._resolved_workflow.steps[step_name]
            input_metadata = (
                metadata if step.input is None else transformed_metadata[step.input]
            )
            transformed_metadata[
                step_name
            ] = step.transformation_handler.transform_metadata(
                input_metadata, annotation=annotation, assume_validated=assume_validated
            )
            assume_validated = True

        return {
            artifact_name: transformed_metadata[step_name]
            for artifact_name, step_name in self._resolved_workflow.artifacts.items()
        }
