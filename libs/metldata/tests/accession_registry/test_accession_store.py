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

"""Testing the accession store."""

import json

import pytest

from metldata.accession_registry.accession_store import AccessionStore
from metldata.config import SubmissionConfig
from tests.fixtures.config import config_sub_fixture  # noqa: F401


def test_empty_store(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
):
    """An empty store file holds no random blocks."""
    accession_store = AccessionStore(config=config_sub_fixture)

    assert accession_store.get_random_blocks(year="26") == set()
    assert not accession_store.exists(year="26", random_block="CBR")


def test_save_per_year(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
):
    """Random blocks are kept per year, so the same block may exist in two years."""
    accession_store = AccessionStore(config=config_sub_fixture)

    accession_store.save(year="26", random_block="CBR")
    accession_store.save(year="26", random_block="JTF")
    accession_store.save(year="27", random_block="CBR")

    assert accession_store.get_random_blocks(year="26") == {"CBR", "JTF"}
    assert accession_store.get_random_blocks(year="27") == {"CBR"}
    assert accession_store.exists(year="27", random_block="CBR")
    assert not accession_store.exists(year="27", random_block="JTF")


def test_save_duplicate_rejected(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
):
    """A random block cannot be saved twice in the same year."""
    accession_store = AccessionStore(config=config_sub_fixture)
    accession_store.save(year="26", random_block="CBR")

    with pytest.raises(AccessionStore.AccessionAlreadyExistsError):
        accession_store.save(year="26", random_block="CBR")


def test_file_format_keeps_legacy(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
):
    """The store is a JSON file with the random blocks per year, and saving keeps
    the legacy accessions in it untouched.
    """
    store_path = config_sub_fixture.accession_store_path
    store_path.write_text(
        json.dumps({"legacy": ["GHGAS12345678901234"], "years": {}}),
        encoding="utf-8",
    )
    accession_store = AccessionStore(config=config_sub_fixture)

    accession_store.save(year="26", random_block="CBR")

    assert json.loads(store_path.read_text(encoding="utf-8")) == {
        "legacy": ["GHGAS12345678901234"],
        "years": {"26": ["CBR"]},
    }
