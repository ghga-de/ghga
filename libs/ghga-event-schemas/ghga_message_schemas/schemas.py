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

"""Read in schemas from json files"""

import json
import os
from pathlib import Path
from typing import Dict, List

_JSON_SCHEMA_DIR = Path(__file__).parent.resolve() / "json_schemas"


def _read_schema(topic_name: str) -> Dict[str, object]:
    """Read schemas from file"""
    with open(
        _JSON_SCHEMA_DIR / f"{topic_name}.json", "r", encoding="utf8"
    ) as schema_file:
        return json.load(schema_file)


def get_topic_names() -> List[str]:
    """Get a list of all topic names."""
    return [
        os.path.splitext(os.path.basename(filename))[0]
        for filename in os.listdir(_JSON_SCHEMA_DIR)
        if filename.endswith(".json")
    ]


SCHEMAS = {topic_name: _read_schema(topic_name) for topic_name in get_topic_names()}
