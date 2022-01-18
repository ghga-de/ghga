# Copyright 2021 - 2022 Universität Tübingen, DKFZ and EMBL
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

"""Check if all JSON schemas are valid"""

import pytest
from jsonschema.validators import validator_for

from ghga_message_schemas import SCHEMAS
from ghga_message_schemas.schemas import get_topic_names


@pytest.mark.parametrize("topic_name", get_topic_names())
def test_json_schemas_valid(topic_name: str):
    """Validate if the schema dicts are valid JSON schemas."""

    schema_dict = SCHEMAS[topic_name]

    validator = validator_for(schema_dict)
    validator.check_schema(schema_dict)
