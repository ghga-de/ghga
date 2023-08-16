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

"""Step definitions for the dataset detail view in the frontend"""

import httpx

from .conftest import TIMEOUT, Config, MongoFixture, scenarios, then, when

scenarios("../features/27_dataset_details.feature")

# TBD: Test more than one dataset, store file checksums etc.


@when(
    "I request the complete-A dataset resource",
    target_fixture="response",
)
def request_test_dataset_resource(config: Config, mongo: MongoFixture):
    # TBD: We fetch the dataset accession from the database, but this should
    # eventually be fetched by browsing the metadata through the mass service
    datasets = mongo.find_documents(
        config.metldata_db_name, "art_embedded_public_class_Dataset", {}
    )
    assert len(datasets) == 6

    for dataset in datasets:
        if dataset["content"]["title"] == "The complete-A dataset":
            accession = dataset["_id"]
            break
    else:
        accession = None

    assert accession, "dataset not found"

    url = (
        f"{config.metldata_url}/artifacts/"
        + f"embedded_public/classes/Dataset/resources/{accession}"
    )
    return httpx.get(url, timeout=TIMEOUT)


@then("the complete-A dataset resource is returned")
def check_test_dataset_resource(response: httpx.Response):
    dataset = response.json()
    assert isinstance(dataset, dict)
    assert dataset["title"] == "The complete-A dataset"
    assert len(dataset["study_files"]) == 1


@when(
    "I request a non-existing dataset resource",
    target_fixture="response",
)
def request_non_existing_dataset_resource(config: Config):
    url = (
        f"{config.metldata_url}/artifacts/"
        + "embedded_public/classes/Dataset/resources/does-not-exist"
    )
    return httpx.get(url, timeout=TIMEOUT)
