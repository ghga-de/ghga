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

import yaml

from tests.fixtures.utils import BASE_DIR

EXAMPLE_METADATA_DIR = BASE_DIR / "example_metadata"


def _get_example_metadata(name: str) -> dict[str, Any]:
    """Get example metadata."""

    with open(EXAMPLE_METADATA_DIR / f"{name}.yaml") as file:
        return yaml.safe_load(file)


VALID_MINIMAL_METADATA_EXAMPLES = [
    _get_example_metadata(f"minimal_metadata_{idx}") for idx in range(1, 3)
]
VALID_MINIMAL_METADATA_EXAMPLE = VALID_MINIMAL_METADATA_EXAMPLES[0]
INVALID_MINIMAL_METADATA_EXAMPLES = [
    _get_example_metadata(f"minimal_metadata_{invalid_example}")
    for invalid_example in [
        "additional_field",
        "missing_field",
        "invalid_enum",
        "invalid_int",
    ]
]
