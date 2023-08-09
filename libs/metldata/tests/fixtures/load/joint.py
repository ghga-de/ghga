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

"""Joint fixture with setup for event content"""

import json
from dataclasses import dataclass
from typing import Any

from ghga_service_commons.api.testing import AsyncTestClient
from hexkit.providers.akafka.testutils import KafkaFixture
from pytest_asyncio import fixture

from metldata.artifacts_rest.artifact_info import ArtifactInfo, load_artifact_info
from metldata.custom_types import Json
from metldata.load.auth import generate_token_and_hash
from metldata.load.config import ArtifactLoaderAPIConfig
from metldata.load.main import get_app
from metldata.load.models import ArtifactResourceDict
from metldata.model_utils.essentials import MetadataModel
from tests.fixtures.load.config import get_config
from tests.fixtures.load.utils import BASE_DIR
from tests.fixtures.mongodb import (  # noqa: F401; pylint: disable=unused-import
    MongoDbFixture,
    mongodb_fixture,
)

ARTIFACT_INFOS_PATH = BASE_DIR / "example_models" / "artifact_infos.json"
ARTIFACT_NAME = "embedded_public"
EMBEDDED_ARTIFACT_PATH = BASE_DIR / "example_metadata" / f"{ARTIFACT_NAME}.json"
EMBEDDED_DATASET_TEST_PATH = BASE_DIR / "example_metadata" / "embedded_dataset.json"
EMBEDDED_ARTIFACT_MODEL_PATH = (
    BASE_DIR / "example_models" / f"{ARTIFACT_NAME}_model.yaml"
)


@dataclass
class JointFixture:
    artifact_infos: list[ArtifactInfo]
    artifact_resources: dict[str, Any]
    client: AsyncTestClient
    config: ArtifactLoaderAPIConfig
    expected_file_resource_content: Json
    expected_embedded_dataset_resource_content: Json
    kafka: KafkaFixture
    mongodb: MongoDbFixture
    token: str


@fixture
async def joint_fixture(
    kafka_fixture: KafkaFixture,
    mongodb_fixture: MongoDbFixture,  # noqa: F811
) -> JointFixture:
    """Get a tuple of a configured test client together with a corresponding token."""

    artifact_infos = [
        load_artifact_info(
            name=ARTIFACT_NAME,
            description=ARTIFACT_NAME,
            model=MetadataModel.init_from_path(EMBEDDED_ARTIFACT_MODEL_PATH),
        )
    ]

    with open(EMBEDDED_ARTIFACT_PATH, "r", encoding="utf-8") as file:
        raw_artifacts = json.load(file)
        artifacts: ArtifactResourceDict = {
            raw_artifacts["type_"]: [raw_artifacts["payload"]["content"]]
        }

    token, token_hash = generate_token_and_hash()

    config = get_config(
        [
            {
                "artifact_infos": artifact_infos,
                "loader_token_hashes": [token_hash],
            },
            kafka_fixture.config,
            mongodb_fixture.config,
        ]
    )

    expected_file_resource_content = artifacts["embedded_public"][0]["study_files"][0]
    expected_embedded_dataset_resource_content = artifacts["embedded_public"][0][
        "embedded_dataset"
    ][1]

    app = await get_app(config=config)
    client = AsyncTestClient(app)
    return JointFixture(
        artifact_infos=artifact_infos,
        artifact_resources=artifacts,
        client=client,
        config=config,
        expected_file_resource_content=expected_file_resource_content,
        expected_embedded_dataset_resource_content=expected_embedded_dataset_resource_content,
        kafka=kafka_fixture,
        mongodb=mongodb_fixture,
        token=token,
    )
