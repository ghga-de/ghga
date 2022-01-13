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
from pathlib import Path
from typing import Dict

_JSON_SCHEMA_DIR = Path(__file__).parent.resolve() / "json_schemas"


def _read_schema(topic_name: str) -> Dict[str, object]:
    """Read schemas from file"""
    with open(
        _JSON_SCHEMA_DIR / f"{topic_name}.json", "r", encoding="utf8"
    ) as schema_file:
        return json.load(schema_file)


DRS_OBJECT_REGISTERED = _read_schema("drs_object_registered")
FILE_INTERNALLY_REGISTERED = _read_schema("file_internally_registered")
FILE_STAGED_FOR_DOWNLOAD = _read_schema("file_staged_for_download")
FILE_UPLOAD_RECEIVED = _read_schema("file_upload_received")
NEW_STUDY_CREATED = _read_schema("new_study_created")
NON_STAGED_FILE_REQUESTED = _read_schema("non_staged_file_requested")
