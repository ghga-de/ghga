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
#

"""Valid and invalid metadata examples using the minimal model."""

from typing import Any

VALID_FILE_EXAMPLES = [
    {
        "alias": "file001",
        "filename": "file001.txt",
        "format": "txt",
        "checksum": "40b971c2b26ffb22db3558d1c27e20f7",
        "size": 15347,
    },
    {
        "alias": "file002",
        "filename": "file002.txt",
        "format": "txt",
        "checksum": "f051753bbb3869485b66b45139fac10b",
        "size": 27653,
    },
]

INVALID_FILE_EXAMPLES = [
    {
        "alias": "file001",
        "filename": "file001.txt",
        "format": "invalid",  # invalid
        "checksum": "40b971c2b26ffb22db3558d1c27e20f7",
        "size": 15347,
    },
    {
        "alias": "file002",
        "filename": "file002.txt",
        "format": "txt",
        "checksum": "f051753bbb3869485b66b45139fac10b",
        "size": 3234.23424,  # invalid
    },
    {
        "alias": "file003",
        # filename missing
        "format": "txt",
        "checksum": "f051753bbb3869485b66b45139fac10b",
        "size": 1123,
    },
    {
        "alias": "file002",
        "filename": "file002.txt",
        "format": "txt",
        "checksum": "f051753bbb3869485b66b45139fac10b",
        "size": 1123,
        "creation_date": "Thu Feb 16 13:15:50 UTC 2023",  # additional field
    },
]

VALID_METADATA_EXAMPLES = [
    {
        "has_dataset": [
            {"alias": "dataset001", "has_file": [VALID_FILE_EXAMPLES[0]["alias"]]},
        ],
        "has_file": [VALID_FILE_EXAMPLES[0]],
    },
    {
        "has_dataset": [
            {"alias": "dataset001", "has_file": [VALID_FILE_EXAMPLES[0]["alias"]]},
            {
                "alias": "dataset001",
                "has_file": [file["alias"] for file in VALID_FILE_EXAMPLES],
            },
        ],
        "has_file": VALID_FILE_EXAMPLES,
    },
]

INVALID_METADATA_EXAMPLES: list[dict[str, Any]] = [  # type: ignore
    {
        "has_dataset": [
            {"alias": "dataset001", "has_file": [VALID_FILE_EXAMPLES[0]["alias"]]},
        ],
    },  # missing field
    {
        "has_dataset": [
            {"alias": "dataset001", "has_file": [VALID_FILE_EXAMPLES[0]["alias"]]},
        ],
        "has_file": VALID_FILE_EXAMPLES[0],
    },  # single file where list expected
] + [
    {
        "has_dataset": [
            {
                "alias": "dataset001",
                "has_file": [VALID_FILE_EXAMPLES[0]["alias"], invalid_file["alias"]],
            },
        ],
        "has_file": [VALID_FILE_EXAMPLES[0], invalid_file],
    }
    for invalid_file in INVALID_FILE_EXAMPLES
]
