# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Test the client module."""

import json
from uuid import uuid4

import httpx2
import pytest
from ghga_service_commons.api.mock_router import MockRouter

from metldata.load.client import upload_artifacts_via_http_api
from metldata.load.collect import get_artifact_topic
from metldata.load.config import ArtifactLoaderClientConfig
from metldata.load.models import ArtifactResourceDict
from tests.fixtures.event_handling import (
    Event,
    FileSystemEventFixture,
    file_system_event_fixture,  # noqa: F401
)

EXAMPLE_ARTIFACTS: ArtifactResourceDict = {
    "example_artifact": [
        {
            "study_accession": "",
            "artifact_name": "example_artifact",
            "content": {"samples": [{"accession": "123test"}]},
        },
    ],
    "added_accessions": [
        {
            "study_accession": "GHGAABC123",
            "artifact_name": "added_accessions",
            "content": {
                "studies": [{"accession": "GHGAABC123"}],
                "samples": [{"accession": "SAMPLE123"}],
            },
        },
    ],
    "stats_public": [
        {
            "study_accession": "",
            "artifact_name": "stats_public",
            "content": {
                "DatasetStats": [
                    {
                        "title": "The complete-A dataset",
                        "dac_email": "dac_institute_a@dac.dac",
                    }
                ],
            },
        }
    ],
}


@pytest.mark.asyncio
async def test_upload_artifacts_via_http_api(
    file_system_event_fixture: FileSystemEventFixture,  # noqa: F811
):
    """Test the happy path of using the upload_artifacts_via_http_api function."""
    token = "some-token"
    config = ArtifactLoaderClientConfig(
        artifact_types=list(EXAMPLE_ARTIFACTS.keys()),
        artifact_topic_prefix="artifact",
        loader_api_root="http://localhost:8000",
        publishable_artifacts=["added_accessions"],
        **file_system_event_fixture.config.model_dump(),
    )

    # publish artifacts:
    artifact_events = [
        Event(
            topic=get_artifact_topic(
                artifact_topic_prefix=config.artifact_topic_prefix,
                artifact_type=artifact_type,
            ),
            type_=artifact_type,
            key=str(uuid4()),  # will later be the submission id
            payload={
                "study_accession": artifact_instance["study_accession"],
                "content": artifact_instance["content"],
            },
        )
        for artifact_type, artifact_instances in EXAMPLE_ARTIFACTS.items()
        for artifact_instance in artifact_instances
    ]
    await file_system_event_fixture.publish_events(artifact_events)

    # mock the api:
    observed_requests: list[httpx2.Request] = []
    router: MockRouter = MockRouter()

    @router.post("/rpc/load-artifacts")
    def load_artifacts(request: httpx2.Request) -> httpx2.Response:
        """Record the request and acknowledge it."""
        observed_requests.append(request)
        return httpx2.Response(status_code=204)

    # upload to api:
    upload_artifacts_via_http_api(
        token=token, config=config, transport=router.as_transport()
    )

    # ensure that the api was called with the expected data:
    assert len(observed_requests) == 1
    assert (
        str(observed_requests[0].url) == f"{config.loader_api_root}/rpc/load-artifacts"
    )
    observed_artifacts = json.loads(observed_requests[0].content.decode("utf-8"))
    assert observed_artifacts == EXAMPLE_ARTIFACTS
    assert observed_requests[0].headers["Authorization"] == f"Bearer {token}"
