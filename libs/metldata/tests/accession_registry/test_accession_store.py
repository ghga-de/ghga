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
from pathlib import Path

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
        "years": {"26": {"CBR": {"retired": []}}},
    }


def test_retire(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
):
    """Retired accessions are kept per study root, each once, and retiring for
    another root leaves them alone.
    """
    accession_store = AccessionStore(config=config_sub_fixture)
    accession_store.save(year="26", random_block="CBR")
    accession_store.save(year="26", random_block="JTF")

    accession_store.retire(year="26", random_block="CBR", retired=["sample-a"])
    accession_store.retire(
        year="26", random_block="CBR", retired=["sample-a", "DS.K7Q"]
    )

    assert accession_store.get_retired(year="26", random_block="CBR") == {
        "sample-a",
        "DS.K7Q",
    }
    assert accession_store.get_retired(year="26", random_block="JTF") == set()


def test_retire_registers_unknown_root(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
):
    """Retiring for a root the store does not know registers the root, so that it is
    not minted again either.
    """
    accession_store = AccessionStore(config=config_sub_fixture)

    accession_store.retire(year="26", random_block="CBR", retired=["sample-a"])

    assert accession_store.exists(year="26", random_block="CBR")
    assert accession_store.get_retired(year="26", random_block="CBR") == {"sample-a"}


FLAT_STORE = "GHGAS12345678901234\nGHGAF98765432109876\n"


def make_flat_store(config: SubmissionConfig, tmp_path: Path) -> AccessionStore:
    """Return an accession store whose file is a flat list of accessions."""
    store_path = tmp_path / "accession_store"
    store_path.write_text(FLAT_STORE, encoding="utf-8")
    return AccessionStore(
        config=config.model_copy(update={"accession_store_path": store_path})
    )


def test_flat_store_rejected(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
    tmp_path: Path,
):
    """A store that is still a flat list of accessions is not a valid store."""
    accession_store = make_flat_store(config_sub_fixture, tmp_path)

    with pytest.raises(AccessionStore.InvalidStoreError):
        accession_store.get_random_blocks(year="26")


def test_migrate_legacy_store(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
    tmp_path: Path,
):
    """Migrating keeps the accessions under `legacy` and the original as backup, after
    which the store takes new random blocks.
    """
    accession_store = make_flat_store(config_sub_fixture, tmp_path)

    accession_store.migrate_legacy_store()
    accession_store.save(year="26", random_block="CBR")

    assert json.loads((tmp_path / "accession_store").read_text(encoding="utf-8")) == {
        "legacy": ["GHGAS12345678901234", "GHGAF98765432109876"],
        "years": {"26": {"CBR": {"retired": []}}},
    }
    assert (tmp_path / "accession_store.bak").read_text(encoding="utf-8") == FLAT_STORE


def test_migrate_twice_rejected(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
    tmp_path: Path,
):
    """A store migrated already is not migrated again, so the backup stays intact."""
    accession_store = make_flat_store(config_sub_fixture, tmp_path)
    accession_store.migrate_legacy_store()

    with pytest.raises(AccessionStore.NotALegacyStoreError):
        accession_store.migrate_legacy_store()

    assert (tmp_path / "accession_store.bak").read_text(encoding="utf-8") == FLAT_STORE
