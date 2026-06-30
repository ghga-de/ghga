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

"""Test object validator"""

import yaml
from linkml_runtime.utils.schemaview import SchemaView

from ghga_validator.my_linkml.object_iterator import ObjectIterator

from .fixtures.utils import BASE_DIR


def test_object_iterator():
    """Test object iterator"""
    file = BASE_DIR / "data" / "example_data_minimal_model.json"

    with open(file, encoding="utf8") as json_file:
        data_json = yaml.safe_load(json_file)

    # Example with the object embedded in the parent object
    schema = BASE_DIR / "schemas" / "minimal_model_parent.yaml"
    target_class = "ParentSubmission"

    list1 = [
        elem for elem in ObjectIterator(SchemaView(schema), data_json, target_class)
    ]

    # Example with the same object on the top level of JSON
    data_json2 = data_json["submissions"][0]
    schema = BASE_DIR / "schemas" / "minimal_model.yaml"
    target_class = "Submission"

    list2 = [
        elem for elem in ObjectIterator(SchemaView(schema), data_json2, target_class)
    ]

    assert len(list2) == 2

    assert len(list1) == len(list2)
    assert list1[0][0:2] == list2[0][0:2]
    assert list1[0][3] != list2[0][3]
