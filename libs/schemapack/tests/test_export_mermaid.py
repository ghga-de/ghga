# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Tests for exporting schemapacks in mermaid format."""

import pytest

from schemapack import export_mermaid, load_schemapack
from tests.fixtures.examples import ERD_PATHS, VALID_SCHEMAPACK_PATHS


@pytest.mark.parametrize(
    "with_properties, file_suffix",
    [(True, "_w_props"), (False, "_wo_props")],
    ids=("content_props", "no_content_props"),
)
def test_export_mermaid(with_properties: bool, file_suffix: str):
    """Test dumping a schemapack in mermaid format."""
    example = "comprehensive_cardinalities_and_types"
    schemapack_path = VALID_SCHEMAPACK_PATHS[example]
    schemapack = load_schemapack(schemapack_path)

    erd_path = ERD_PATHS[example + file_suffix]

    observed_output = export_mermaid(
        schemapack=schemapack, content_properties=with_properties
    )
    assert observed_output == erd_path.read_text().strip()
