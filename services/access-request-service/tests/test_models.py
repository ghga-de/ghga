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
#

"""Test the validation of the core models"""

import pytest
from pydantic import TypeAdapter, ValidationError

from ars.core.models import Accession


@pytest.mark.parametrize(
    "accession",
    ["GHGAD12345678901234", "GHGA.26.ABC.1.DS.XYZ"],
)
def test_good_accession(accession: str):
    """Test that legacy and new dataset accessions are accepted."""
    assert TypeAdapter(Accession).validate_python(accession) == accession


@pytest.mark.parametrize(
    "accession",
    [
        "hello",
        "GHGA.26",
        "GHGA.26.ABC.1",
        "GHGA.26.ABC.1.sample_a",
        "GHGA.26.AB1.1.DS.XYZ",
        "GHGA.2026.ABC.1.DS.XYZ",
    ],
)
def test_bad_accession(accession: str):
    """Test that study PIDs, other entities' accessions and malformed ones are rejected."""
    with pytest.raises(ValidationError):
        TypeAdapter(Accession).validate_python(accession)
