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

"""Step definitions for combination of searching, filtering and pagination"""

from .conftest import JointFixture, parse, scenarios, when
from .utils import search_dataset_rpc

scenarios("../features/25_combined_browsing.feature")


@when(
    parse('I search "{query}" and request page "{page:d}" with page size "{size:d}"'),
    target_fixture="response",
)
def search_items_with_pagination(
    fixtures: JointFixture, query: str, page: int, size: int
):
    limit = size
    skip = (page - 1) * size
    return search_dataset_rpc(fixtures=fixtures, query=query, limit=limit, skip=skip)


@when(
    parse('I search "{query}" in datasets with type "{dataset_type}"'),
    target_fixture="response",
)
def search_and_filter_dataset(fixtures: JointFixture, query: str, dataset_type: str):
    filters = [{"key": "types", "value": dataset_type}]
    return search_dataset_rpc(fixtures=fixtures, filters=filters, query=query)


@when(
    parse('I filter dataset with type "{dataset_type}"'),
    target_fixture="response",
)
def search_dataset(fixtures: JointFixture, dataset_type):
    filters = [{"key": "types", "value": dataset_type}]
    return search_dataset_rpc(fixtures=fixtures, filters=filters)
