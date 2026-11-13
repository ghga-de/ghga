# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Test that the metadata config gives the add_accessions step its study class."""

from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from ghga_datasteward_kit.metadata import MetadataConfig
from tests.fixtures.metadata import METADATA_CONFIG_PATH


def load_config_values() -> dict[str, Any]:
    """Load the values of the metadata config fixture."""
    return yaml.safe_load(METADATA_CONFIG_PATH.read_text())


@pytest.mark.parametrize(
    "add_accessions_study_class_name",
    [None, "Investigation"],
    ids=["unset", "same"],
)
def test_study_class_name_shared(add_accessions_study_class_name: str | None):
    """The add_accessions step takes the top-level study class, unless it sets the
    same one itself.
    """
    values = load_config_values()
    values["study_class_name"] = "Investigation"
    if add_accessions_study_class_name is not None:
        values["workflow_config"]["add_accessions"]["study_class_name"] = (
            add_accessions_study_class_name
        )

    config = MetadataConfig(**values)

    assert config.workflow_config.add_accessions.study_class_name == "Investigation"


def test_study_class_name_mismatch():
    """An add_accessions step setting a different study class is rejected."""
    values = load_config_values()
    values["workflow_config"]["add_accessions"]["study_class_name"] = "Investigation"

    with pytest.raises(ValidationError, match="Set it only at the top level"):
        MetadataConfig(**values)
