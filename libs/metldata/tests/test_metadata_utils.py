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
    convert_resource_list_to_dict,
    get_resources_of_class,
    lookup_resource_by_identifier,
    upsert_resources_in_metadata,
)
from metldata.model_utils.anchors import AnchorPoint, get_anchors_points_by_target
from tests.fixtures.metadata import VALID_MINIMAL_METADATA_EXAMPLE
from tests.fixtures.metadata_models import VALID_MINIMAL_METADATA_MODEL


def test_lookup_resource_by_identifier_happy():
    """Test the happy path of using the lookup_resource_by_identifier function."""

    identifier = "test_sample_01_R1"
    resource_dict = convert_resource_list_to_dict(
        resources=VALID_MINIMAL_METADATA_EXAMPLE["files"], identifier_slot="alias"
    )
    expected_resource = resource_dict[identifier]

    anchor_points_by_target = get_anchors_points_by_target(
        model=VALID_MINIMAL_METADATA_MODEL
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
        model=VALID_MINIMAL_METADATA_MODEL
    )

    with pytest.raises(MetadataResourceNotFoundError):
        _ = lookup_resource_by_identifier(
            class_name="File",
            global_metadata=VALID_MINIMAL_METADATA_EXAMPLE,
            identifier=identifier,
            anchor_points_by_target=anchor_points_by_target,
        )


EXAMPLE_GLOBAL_METADATA = {
    "files": [
        {
            "alias": "test_sample_01_R1",
            "file_format": "fastq",
            "file_size": 1234567890,
        },
        {
            "alias": "test_sample_01_R2",
            "file_format": "fastq",
            "file_size": 1234567890,
        },
    ]
}

EXAMPLE_ANCHOR_POINTS_BY_TARGET = {
    "File": AnchorPoint(target_class="File", identifier_slot="alias", root_slot="files")
}


def test_get_resources_of_class_happy():
    """Test the happy path of using the get_resources_of_class function."""

    expected_resources = EXAMPLE_GLOBAL_METADATA["files"]

    observed_resources = get_resources_of_class(
        class_name="File",
        global_metadata=EXAMPLE_GLOBAL_METADATA,
        anchor_points_by_target=EXAMPLE_ANCHOR_POINTS_BY_TARGET,
    )

    assert observed_resources == expected_resources


def test_update_resources_in_metadata_happy():
    """Test the happy path of using the update_resources_in_metadata function."""

    modified_resources = [
        {
            "alias": "test_sample_01_R1",
            "file_format": "fastq",
            "some_new_field": "some_new_value",
        },
        {
            "alias": "test_sample_01_R2",
            "file_format": "fastq",
            "some_new_field": "some_new_value",
        },
    ]

    expected_metadata = {"files": modified_resources}

    observed_metadata = upsert_resources_in_metadata(
        resources=modified_resources,
        class_name="File",
        global_metadata=EXAMPLE_GLOBAL_METADATA,
        anchor_points_by_target=EXAMPLE_ANCHOR_POINTS_BY_TARGET,
    )

    assert observed_metadata == expected_metadata
