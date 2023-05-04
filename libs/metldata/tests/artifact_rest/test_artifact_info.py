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

"""Test the artifact_info module."""

from metldata.artifacts_rest.artifact_info import (
    load_artifact_info,
    subset_json_schema_for_class,
)
from tests.fixtures.metadata_models import VALID_MINIMAL_METADATA_MODEL


def test_subset_json_schema_for_class():
    """Test happy path of using subset_json_schema_for_class."""

    # a global schema that uses File and Dataset definitions on the top level:
    global_json_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "properties": {
            "datasets": {
                "items": {
                    "additionalProperties": {"$ref": "#/$defs/Dataset"},
                    "type": "object",
                },
                "type": "array",
            },
            "files": {
                "items": {
                    "additionalProperties": {"$ref": "#/$defs/File"},
                    "type": "object",
                },
                "type": "array",
            },
        },
        "required": ["files", "datasets"],
        "type": "object",
        "$defs": {
            "Dataset": {
                "properties": {
                    "files": {
                        "items": {
                            "additionalProperties": {"$ref": "#/$defs/File"},
                            "type": "object",
                        },
                        "type": "array",
                    }
                },
                "required": ["files"],
                "type": "object",
            },
            "File": {
                "properties": {
                    "checksum": {"type": "string"},
                    "size": {"type": "integer"},
                },
                "required": ["size", "checksum"],
                "type": "object",
            },
        },
    }

    # generate a subset schema for the Dataset class:
    observed_subschema = subset_json_schema_for_class(
        global_json_schema=global_json_schema, class_name="Dataset"
    )

    # the subset schema should only contain the File defintion as it is used by the
    # Dataset class:
    expected_subschema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "properties": {
            "files": {
                "items": {
                    "additionalProperties": {"$ref": "#/$defs/File"},
                    "type": "object",
                },
                "type": "array",
            }
        },
        "required": ["files"],
        "type": "object",
        "$defs": {
            "File": {
                "properties": {
                    "checksum": {"type": "string"},
                    "size": {"type": "integer"},
                },
                "required": ["size", "checksum"],
                "type": "object",
            },
        },
    }
    assert observed_subschema == expected_subschema


def test_load_artifact_info():
    """Test happy path of using load_artifact_info."""

    expected_artifact_name = "test_artifact"
    expected_artifact_description = "This is a test artifact."
    expected_resource_class_names = {"File", "Dataset"}

    artifact_info = load_artifact_info(
        model=VALID_MINIMAL_METADATA_MODEL,
        name=expected_artifact_name,
        description=expected_artifact_description,
    )

    assert artifact_info.name == expected_artifact_name
    assert artifact_info.description == expected_artifact_description
    assert artifact_info.resource_classes.keys() == expected_resource_class_names
