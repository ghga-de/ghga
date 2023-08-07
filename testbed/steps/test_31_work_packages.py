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

"""Step definitions for work package tests"""

import httpx

from example_data.datasets import DATASET_OVERVIEW_EVENT

from .conftest import (
    TIMEOUT,
    Config,
    JointFixture,
    LoginFixture,
    MongoFixture,
    async_step,
    given,
    scenarios,
    set_state,
    then,
    unset_state,
    when,
)

scenarios("../features/31_work_packages.feature")


@given("no work packages have been created yet")
def wps_database_is_empty(config: Config, mongo: MongoFixture):
    mongo.empty_databases(config.wps_db_name)
    unset_state("a download token has been created", mongo)


@given("the test dataset has been announced")
@async_step
async def announce_dataset(config: Config, fixtures: JointFixture):
    # TBD: Should actually happen during upload, not here

    # Add accessions using the metldata database
    study_files = fixtures.mongo.find_documents(
        config.metldata_db_name, "art_embedded_public_class_StudyFile", {}
    )
    assert len(study_files) == 1
    study_files = [study_file["content"] for study_file in study_files]
    alias_to_accession = {
        study_file["alias"]: study_file["accession"] for study_file in study_files
    }
    payload = DATASET_OVERVIEW_EVENT.dict()
    payload_files = payload["files"]
    for payload_file in payload_files:
        payload_file["accession"] = alias_to_accession[payload_file["accession"]]

    # publish dataset overview event
    await fixtures.kafka.publisher.publish(
        payload=payload,
        type_="metadata_dataset_overview",
        key="metadata-1",
        topic="metadata",
    )
    # wait until the event has been processed
    assert fixtures.mongo.wait_for_document(
        config.wps_db_name, "datasets", {"_id": payload["accession"]}
    )


@when("the list of datasets is queried", target_fixture="response")
def query_datasets(config: Config, login: LoginFixture):
    user_id = login.user["_id"]
    url = f"{config.wps_url}/users/{user_id}/datasets"
    return httpx.get(url, headers=login.headers, timeout=TIMEOUT)


@then("the test dataset is in the response list")
def check_dataset_in_list(response: httpx.Response):
    data = response.json()
    dataset = DATASET_OVERVIEW_EVENT
    files = DATASET_OVERVIEW_EVENT.files
    for file in (data[0] if data else {}).get("files", []):
        file.pop("id", None)
    assert data == [
        {
            "id": dataset.accession,
            "description": dataset.description,
            "stage": dataset.stage.value,  # pylint: disable=no-member
            "title": dataset.title,
            "files": [
                {"extension": file.file_extension}
                for file in files  # pylint: disable=not-an-iterable
            ],
        }
    ]


@when("a work package for the test dataset is created", target_fixture="response")
def create_work_package(login: LoginFixture, fixtures: JointFixture):
    data = {
        "dataset_id": DATASET_OVERVIEW_EVENT.accession,
        "type": "download",
        "file_ids": None,
        "user_public_crypt4gh_key": fixtures.config.user_public_crypt4gh_key,
    }
    url = f"{fixtures.config.wps_url}/work-packages"
    response = httpx.post(url, headers=login.headers, json=data, timeout=TIMEOUT)
    return response


@then("the response contains a download token for the test dataset")
def check_download_token(fixtures: JointFixture, response: httpx.Response):
    data = response.json()
    assert set(data) == {"id", "token"}
    id_, token = data["id"], data["token"]
    assert 20 <= len(id_) < 40 and 80 < len(token) < 120
    id_and_token = f"{id_}:{token}"
    work_package = fixtures.mongo.find_document(
        fixtures.config.wps_db_name, "workPackages", {"_id": id_}
    )
    assert work_package
    assert work_package["type"] == "download"
    assert work_package["dataset_id"] == DATASET_OVERVIEW_EVENT.accession
    set_state("a download token has been created", id_and_token, fixtures.mongo)
