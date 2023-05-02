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

"""Test the essentials module."""

from copy import deepcopy

from linkml_runtime import SchemaView

from metldata.model_utils.essentials import MetadataModel
from tests.fixtures.metadata_models import (
    VALID_MINIMAL_METADATA_MODEL,
    VALID_MINIMAL_MODEL_EXAMPLE_PATH,
)


def test_metadata_model_from_path():
    """Test the MetadataModel creation from path."""

    model = MetadataModel.init_from_path(VALID_MINIMAL_MODEL_EXAMPLE_PATH)

    assert model.name == "Minimal-Model"


def test_metadata_model_get_schema_view():
    """Test getting a schema view from a MetadataModel."""

    schema_view = VALID_MINIMAL_METADATA_MODEL.schema_view

    assert isinstance(schema_view, SchemaView)


def test_metadata_model_temporary_yaml():
    """Test getting a temporary yaml file from a MetadataModel."""

    model = deepcopy(VALID_MINIMAL_METADATA_MODEL)

    # modify the model:
    model.name = "Test-Model-Modified"

    # get a temporary yaml file:
    with model.temporary_yaml_path() as model_path:
        # load a copy of that file into a new model instance:
        model_copy = MetadataModel.init_from_path(model_path)

    assert model_copy == model
