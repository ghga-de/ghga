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

"""Step definitions for pagination of datasets in the frontend"""

from .conftest import JointFixture, parse, scenarios, when
from .utils import search_dataset_rpc

scenarios("../features/24_paginate_datasets.feature")


@when(
    parse('I request page "{page_num:d}" with a page size of "{page_size:d}"'),
    target_fixture="response",
)
def request_page_with_page_size(fixtures: JointFixture, page_num: int, page_size: int):
    limit = page_size
    skip = (page_num - 1) * page_size
    return search_dataset_rpc(fixtures=fixtures, limit=limit, skip=skip)
