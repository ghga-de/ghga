# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Test the identifiers module."""

from metldata.model_utils.identifiers import get_class_identifiers
from tests.fixtures.metadata_models import VALID_MINIMAL_METADATA_MODEL


def test_get_class_identifiers_happy():
    """Test the happy path of using the get_class_identifiers function."""
    expected_identifiers = {"File": "alias", "Dataset": "alias"}

    observed_identifiers = get_class_identifiers(model=VALID_MINIMAL_METADATA_MODEL)

    assert observed_identifiers == expected_identifiers
