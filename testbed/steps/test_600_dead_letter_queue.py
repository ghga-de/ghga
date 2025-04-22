# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Step definitions for Dead Letter Queue"""

import json
import time

from fixtures.http_client import HttpClient
from fixtures.kafka import EventDetails
from ghga_event_schemas.pydantic_ import (
    MetadataDatasetFile,
    MetadataDatasetOverview,
    MetadataDatasetStage,
)

from .conftest import JointFixture, given, parse, scenarios, then, when

scenarios("../features/600_dead_letter_queue.feature")


@given("the dead letter queue is empty")
def clear_dlq(
    fixtures: JointFixture,
):
    """Clear the dead letter queue."""
    fixtures.kafka.clear_topics(
        topics=fixtures.config.dlq_topic,
    )
    fixtures.mongo.empty_databases(
        db_names=[fixtures.config.dlq_db_name],
    )


@when(
    parse('"{event}" event has been published with an invalid schema'),
    target_fixture="dlq_event",
)
def publish_event(
    event: str,
    fixtures: JointFixture,
):
    event_topic_type_map = {
        "dataset creation": (
            fixtures.config.dataset_change_topic,
            fixtures.config.dataset_created_type,
        ),
        "file deletion": (
            fixtures.config.file_deletion_request_topic,
            fixtures.config.file_deletion_request_type,
        ),
        "access request": (
            fixtures.config.access_request_topic,
            fixtures.config.access_request_created_type,
        ),
        "resource creation": (
            fixtures.config.resource_change_topic,
            fixtures.config.resource_change_type,
        ),
        "notification": (
            fixtures.config.notification_topic,
            fixtures.config.notification_type,
        ),
    }

    event_details = EventDetails(
        key="testing_invalid_event_payload",
        topic=event_topic_type_map[event][0],
        type_=event_topic_type_map[event][1],
        payload={"invalid": "payload"},
    )
    fixtures.kafka.publish_event(
        event_details=event_details,
    )
    # Wait for the event to be processed
    return event_details


@then(parse('"{full_service_name}" has published the event to the dead letter queue'))
def check_dlq_for_event(
    full_service_name: str,
    fixtures: JointFixture,
    http: HttpClient,
    dlq_event: EventDetails,
):
    """Check if the event is in the dead letter queue"""
    dlqs = fixtures.state.get_state("dlqs") or []
    auth_headers = {"Authorization": f"Bearer {fixtures.config.dlq_token}"}
    service_name = fixtures.config.service_short_names[full_service_name]
    url = f"{fixtures.config.dlq_url}/{service_name}/{dlq_event.topic}"

    timeout = 5  # seconds
    interval = 0.5
    elapsed_time = 0.0

    while elapsed_time < timeout:
        response = http.get(url, headers=auth_headers)
        if response.status_code == 200:
            results = response.json()
            if len(results) == 1 and results[0]["key"] == dlq_event.key:
                assert results[0]["type_"] == dlq_event.type_
                assert "dlq_id" in results[0]
                dlq_event.dlq_id = results[0]["dlq_id"]

                dlqs.append(results[0]["dlq_id"])
                fixtures.state.set_state("dlqs", dlqs)
                return
        time.sleep(interval)
        elapsed_time += interval
    raise AssertionError(f"Event not found in DLQ within {timeout} seconds")


@when("all events in the dead letter queue have been deleted")
def delete_dlq_events(
    fixtures: JointFixture,
):
    dlqs = fixtures.state.get_state("dlqs") or []
    auth_headers = {"Authorization": f"Bearer {fixtures.config.dlq_token}"}
    for dlq_id in dlqs:
        url = f"{fixtures.config.dlq_url}/{dlq_id}"
        response = fixtures.http.delete(url, headers=auth_headers)
        assert response.status_code == 204, (
            f"Failed to delete DLQ event {dlq_id}: {response.text}"
        )


@then("there is no event in the dead letter queue")
def check_no_dlq_events(fixtures: JointFixture):
    dlq_events = fixtures.mongo.wait_for_documents(
        fixtures.config.dlq_db_name,
        "dlqEvents",
        {},
        timeout=5,
    )
    assert not dlq_events


@when(
    "the corrected dataset creation event has been republished to the dataset information service",
    target_fixture="corrected_payload",
)
def publish_corrected_event(
    fixtures: JointFixture,
    dlq_event: EventDetails,
):
    """Publish the corrected event."""
    assert dlq_event.dlq_id is not None, "DLQ event ID is not set"

    corrected_payload = MetadataDatasetOverview(
        accession=dlq_event.dlq_id,
        title="Restored from DLQ",
        stage=MetadataDatasetStage.UPLOAD,
        description=None,
        files=[
            MetadataDatasetFile(
                accession="GHGAF123",
                description=None,
                file_extension=".example",
            )
        ],
    )

    request_body = {
        "dlq_id": dlq_event.dlq_id,
        "override": {
            "topic": dlq_event.topic,
            "type_": dlq_event.type_,
            "payload": corrected_payload.model_dump(),
            "key": dlq_event.key,
        },
    }

    auth_headers = {"Authorization": f"Bearer {fixtures.config.dlq_token}"}
    url = f"{fixtures.config.dlq_url}/dins/{dlq_event.topic}"
    response = fixtures.http.post(url, json=request_body, headers=auth_headers)
    assert response.status_code == 200, f"Failed to delete DLQ event: {response.text}"
    return corrected_payload


@then("the dataset is known to the dataset information service")
def check_dataset_information(
    fixtures: JointFixture,
    dlq_event: EventDetails,
    corrected_payload: MetadataDatasetOverview,
):
    """Check if the dataset is known to the dataset information service."""
    url = f"{fixtures.config.dins_url}/dataset_information/{dlq_event.dlq_id}"
    response = fixtures.http.get(url)
    assert response.status_code == 200, f"Failed to get dataset: {response.text}"
    result = response.json()
    assert result["accession"] == dlq_event.dlq_id
    assert result["file_information"] == [
        {"accession": file.accession} for file in corrected_payload.files
    ]
