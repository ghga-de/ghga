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

"""Testing the accession handler."""

from metldata.accession_registry.accession_store import AccessionStore
from metldata.config import SubmissionConfig
from tests.fixtures.config import config_sub_fixture  # noqa: F401


def test_accession_store_happy(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
):
    """Test accession store happy path."""

    expected_accessions = ["accession001", "accession002"]

    accession_store = AccessionStore(config=config_sub_fixture)

    # save accessions
    for expected_accession in expected_accessions:
        accession_store.save(accession=expected_accession)

    # check that the expected accessions exist:
    for expected_accession in expected_accessions:
        assert accession_store.exists(accession=expected_accession)


def test_accession_store_unkown_accession(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
):
    """Test accession store happy path."""

    unknown_accession = "accession003"

    accession_store = AccessionStore(config=config_sub_fixture)
    assert not accession_store.exists(accession=unknown_accession)
