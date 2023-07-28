# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Step definitions for metadata browsing tests"""


import httpx

from .conftest import (
    METLDATA_DB_NAME,
    METLDATA_URL,
    TIMEOUT,
    MongoFixture,
    parse,
    scenarios,
    then,
    when,
)

scenarios("../features/20_browse_metadata.feature")


@when("I request info on all available artifacts", target_fixture="response")
def request_info_on_artifacts():
    url = f"{METLDATA_URL}/artifacts"
    return httpx.options(url, timeout=TIMEOUT)


@then("I get the expected info on all the artifacts")
def check_artifacts(response: httpx.Response):
    artifact_infos = response.json()
    assert isinstance(artifact_infos, list)
    assert len(artifact_infos) == 4
    artifacts = {artifact["name"]: artifact for artifact in artifact_infos}
    assert sorted(artifacts) == [
        "embedded_public",
        "embedded_restricted",
        "resolved_public",
        "resolved_restricted",
    ]
    resolved_public_classes = artifacts["resolved_public"]["resource_classes"]
    assert "Dataset" in resolved_public_classes
    assert "EmbeddedDataset" not in resolved_public_classes
    assert len(resolved_public_classes) == 20
    embedded_public_classes = artifacts["embedded_public"]["resource_classes"]
    assert set(resolved_public_classes).issubset(embedded_public_classes)
    assert "EmbeddedDataset" in embedded_public_classes


@when(
    parse('I request info on the "{artifact_name}" artifact'), target_fixture="response"
)
def request_info_on_artifact(artifact_name: str):
    url = f"{METLDATA_URL}/artifacts/{artifact_name}"
    return httpx.options(url, timeout=TIMEOUT)


@then(parse('I get the expected info on the "{artifact_name}" artifact'))
def check_artifact(artifact_name, response: httpx.Response):
    artifact_info = response.json()
    assert isinstance(artifact_info, dict)
    assert artifact_info["name"] == artifact_name
    classes = artifact_info["resource_classes"]
    num_additional_classes = 1 if artifact_name.startswith("embedded") else 0
    assert len(classes) == 20 + num_additional_classes


@when(
    "I request the test dataset resource",
    target_fixture="response",
)
def request_test_dataset_resource(mongo: MongoFixture):
    # TBD: We fetch the dataset accession from the database, but this should
    # eventually be fetched by browsing the metadata through the mass service
    datasets = mongo.find_documents(
        METLDATA_DB_NAME, "art_embedded_public_class_Dataset", {}
    )
    assert len(datasets) == 1
    accession = datasets[0]["_id"]

    url = (
        f"{METLDATA_URL}/artifacts/"
        + f"embedded_public/classes/Dataset/resources/{accession}"
    )
    return httpx.get(url, timeout=TIMEOUT)


@then("the test dataset resource is returned")
def check_test_dataset_resource(response: httpx.Response):
    dataset = response.json()
    assert isinstance(dataset, dict)
    assert dataset["alias"] == "DS_1"
    assert dataset["description"] == "An interesting dataset A"
    assert len(dataset["study_files"]) == 2


@when(
    "I request a non-existing dataset resource",
    target_fixture="response",
)
def request_non_existing_dataset_resource():
    url = (
        f"{METLDATA_URL}/artifacts/"
        + "embedded_public/classes/Dataset/resources/does-not-exist"
    )
    return httpx.get(url, timeout=TIMEOUT)
