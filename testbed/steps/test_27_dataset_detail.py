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

import re

import httpx

from .conftest import (
    TIMEOUT,
    Config,
    MongoFixture,
    get_state,
    parse,
    scenarios,
    then,
    when,
)
from .utils import get_dataset_overview

scenarios("../features/27_dataset_details.feature")


@when(parse('I request the details of "{alias}" dataset'), target_fixture="response")
def request_dataset_details(
    alias: str, config: Config, mongo: MongoFixture
) -> httpx.Response:
    datasets = get_state("all available datasets", mongo)
    if alias == "non-existing":
        resource_id = alias
    else:
        assert alias in datasets
        resource_id = datasets[alias]["accession"]
    url = (
        f"{config.metldata_url}/artifacts/"
        f"embedded_public/classes/EmbeddedDataset/resources/{resource_id}"
    )
    return httpx.get(url, timeout=TIMEOUT)


@then(parse('I get the details of "{alias}" dataset'))
def check_dataset_details(alias: str, response: httpx.Response, mongo: MongoFixture):
    result = response.json()
    assert result
    assert alias == result.get("alias")
    datasets = get_state("all available datasets", mongo)
    assert alias in datasets
    overview = get_dataset_overview(result)
    assert overview == datasets[alias]


@when(parse("I request an associated sample resource"), target_fixture="response")
def request_one_associated_samples(
    config: Config, response: httpx.Response
) -> httpx.Response:
    result = response.json()
    match = re.search("'sample': '(GHGAN[0-9]+)'", repr(result))
    assert match
    resource_id = match.group(1)
    url = (
        f"{config.metldata_url}/artifacts/"
        f"embedded_public/classes/Sample/resources/{resource_id}"
    )
    return httpx.get(url, timeout=TIMEOUT)


@then("I get a sample resource")
def check_one_sample_resource(response: httpx.Response):
    result = response.json()
    assert isinstance(result, dict)
    assert sorted(result) == [
        "accession",
        "alias",
        "biospecimen",
        "condition",
        "description",
        "isolation",
        "name",
        "sample_files",
        "sequencing_processes",
        "storage",
        "type",
    ]
