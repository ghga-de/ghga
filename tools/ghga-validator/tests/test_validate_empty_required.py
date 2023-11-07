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

"""Test validating empty data when there are required fields defined in schema"""

import os

from ghga_validator.cli import validate_json_file

from .fixtures.utils import BASE_DIR


def test_validate_empty_required():
    """Test validating empty data when there are required fields defined in schema"""
    schema = BASE_DIR / "schemas" / "example_schema_required.yaml"
    file = BASE_DIR / "data" / "example_data_empty.json"
    report = BASE_DIR / "tmp.json"
    target_class = "TextAnalysis"

    assert validate_json_file(file, schema, report, str(target_class)) is False
    if os.path.exists(report):
        os.remove(report)
