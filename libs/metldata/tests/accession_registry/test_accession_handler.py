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

from metldata.accession_registry.accession_handler import AccessionHandler
from metldata.accession_registry.accession_store import AccessionStore
from metldata.config import Config
from tests.fixtures.config import config_fixture  # noqa: F401


def test_get_accession_happy(config_fixture: Config):  # noqa: F811
    """Test the happy path of getting 10 accession for each resource type."""

    accession_store = AccessionStore(config=config_fixture)
    accession_handler = AccessionHandler(
        config=config_fixture, accession_store=accession_store
    )

    accessions = []
    for resource_type in config_fixture.prefix_mapping:
        for _ in range(10):
            # generate 10 accessions for each resource type
            expected_prefix = config_fixture.prefix_mapping[resource_type]
            expected_length = len(expected_prefix) + config_fixture.suffix_length

            accession = accession_handler.get_accession(resource_type=resource_type)

            assert accession.startswith(expected_prefix)
            assert len(accession) == expected_length

            accessions.append(accession)

    # check whether all theses accessions have been stored:
    for accession in accessions:
        assert accession_store.exists(accession=accession)
