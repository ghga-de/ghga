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

"""Step definitions for metadata searching tests"""

import httpx

from .conftest import Config, MongoFixture, given, parse, scenarios, then, when
from .utils import search_dataset_rpc

scenarios("../features/22_search_datasets.feature")


@given("the database collection is prepared for searching")
def index_mass_collection(config: Config, mongo: MongoFixture):
    mongo.index_collection(
        db_name=config.mass_db_name, collection_name=config.mass_collection
    )


@when("I search documents with invalid query format", target_fixture="response")
def search_with_invalid_query(config: Config):
    invalid_query = {"Invalid": "Query"}
    return search_dataset_rpc(config=config, query=invalid_query)  # type: ignore


@when(
    parse('I search datasets with the "{keyword}" query'),
    target_fixture="response",
)
def search_dataset(config: Config, keyword):
    return search_dataset_rpc(config, query=keyword)


@then("I get the expected results from study search")
def check_study_search_result(response: httpx.Response):
    results = response.json()
    assert results["count"] == 1
    hits = results["hits"]
    assert hits[0]["content"]["studies"][0]["alias"] == "STUDY_A"


@then("I get the expected results from description search")
def check_description_search_result(response: httpx.Response):
    results = response.json()
    assert results["count"] == 1
    hits = results["hits"]
    assert hits[0]["content"]["description"] == "An interesting dataset B"
