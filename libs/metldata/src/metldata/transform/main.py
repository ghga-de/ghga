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

"""Main logic for running a transformation workflow on submissions."""


from collections.abc import Awaitable
from typing import Callable

from metldata.event_handling.event_handling import (
    FileSystemEventPublisher,
    FileSystemEventSubscriber,
)
from metldata.event_handling.models import SubmissionEventPayload
from metldata.model_utils.essentials import MetadataModel
from metldata.transform.artifact_publisher import ArtifactEvent, ArtifactEventPublisher
from metldata.transform.base import WorkflowConfig, WorkflowDefinition
from metldata.transform.config import TransformationEventHandlingConfig
from metldata.transform.handling import WorkflowHandler
from metldata.transform.source_event_subscriber import SourceEventSubscriber


async def run_workflow_on_source_event(
    source_event: SubmissionEventPayload,
    workflow_handler: WorkflowHandler,
    publish_artifact_func: Callable[[ArtifactEvent], Awaitable[None]],
) -> None:
    """Run a transformation workflow on a source event and publish the artifact using
    the provided artifact publisher.

    Args:
        source_event:
            The source event corresponding to one submission and its cotent.
        workflow_handler:
            The workflow handler preconfigured with a workflow definition, a workflow
            config, and the original model of the source events.
        publish_artifact_func: A function for publishing artifacts.
    """
    artifacts = workflow_handler.run(
        metadata=source_event.content, annotation=source_event.annotation
    )

    for artifact_type, artifact_content in artifacts.items():
        artifact_event = ArtifactEvent(
            artifact_type=artifact_type,
            payload=source_event.model_copy(update={"content": artifact_content}),
        )

        await publish_artifact_func(artifact_event)


async def run_workflow_on_all_source_events(
    *,
    event_config: TransformationEventHandlingConfig,
    workflow_definition: WorkflowDefinition,
    worflow_config: WorkflowConfig,
    original_model: MetadataModel,
):
    """Run a subscriber to hand source events to a transformation workflow and
    run a publisher for publishing artifacts.
    """
    workflow_handler = WorkflowHandler(
        workflow_definition=workflow_definition,
        workflow_config=worflow_config,
        original_model=original_model,
    )
    event_publisher = FileSystemEventPublisher(config=event_config)
    artifact_publisher = ArtifactEventPublisher(
        config=event_config, provider=event_publisher
    )
    source_event_subscriber = SourceEventSubscriber(
        config=event_config,
        run_workflow_func=lambda source_event: run_workflow_on_source_event(
            workflow_handler=workflow_handler,
            source_event=source_event,
            publish_artifact_func=artifact_publisher.publish_artifact,
        ),
    )
    event_subscriber = FileSystemEventSubscriber(
        config=event_config, translator=source_event_subscriber
    )
    await event_subscriber.run()
