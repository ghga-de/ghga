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

"""Test the metadata utils."""


import pytest

from metldata.metadata_utils import (
    MetadataResourceNotFoundError,
    lookup_resource_by_identifier,
)
from metldata.model_utils.anchors import get_anchors_points_by_target
from tests.fixtures.metadata import VALID_MINIMAL_METADATA_EXAMPLE
from tests.fixtures.metadata_models import MINIMAL_VALID_METADATA_MODEL


def test_lookup_resource_by_identifier_happy():
    """Test the happy path of using the lookup_resource_by_identifier function."""

    identifier = "test_sample_01_R1"
    expected_resource = VALID_MINIMAL_METADATA_EXAMPLE["has_file"][identifier]
    expected_resource["alias"] = identifier

    anchor_points_by_target = get_anchors_points_by_target(
        model=MINIMAL_VALID_METADATA_MODEL
    )
    observed_resource = lookup_resource_by_identifier(
        class_name="File",
        global_metadata=VALID_MINIMAL_METADATA_EXAMPLE,
        identifier=identifier,
        anchor_points_by_target=anchor_points_by_target,
    )

    assert observed_resource == expected_resource


def test_lookup_resource_by_identifier_not_exist():
    """Test the using the lookup_resource_by_identifier function with an identifier
    that does not exist."""

    identifier = "non_existing_identifier"

    anchor_points_by_target = get_anchors_points_by_target(
        model=MINIMAL_VALID_METADATA_MODEL
    )

    with pytest.raises(MetadataResourceNotFoundError):
        _ = lookup_resource_by_identifier(
            class_name="File",
            global_metadata=VALID_MINIMAL_METADATA_EXAMPLE,
            identifier=identifier,
            anchor_points_by_target=anchor_points_by_target,
        )
