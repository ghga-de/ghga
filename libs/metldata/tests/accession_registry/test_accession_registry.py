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

"""Testing the accession registry."""

import re

import pytest

from ghga_service_commons.utils.accessions import (
    BASE32_ALPHABET,
    DATASET_PID_PATTERN,
    DATASET_PID_PREFIX,
    STUDY_PID_PATTERN,
    STUDY_PID_PREFIX,
)
from ghga_service_commons.utils.utc_dates import now_as_utc
from metldata.accession_registry import accession_registry as accession_registry_module
from metldata.accession_registry.accession_registry import AccessionRegistry
from metldata.accession_registry.accession_store import AccessionStore
from metldata.config import SubmissionConfig
from tests.fixtures.config import config_sub_fixture  # noqa: F401


def make_registry(config: SubmissionConfig) -> tuple[AccessionRegistry, AccessionStore]:
    """Build an accession registry and its store from the config."""
    accession_store = AccessionStore(config=config)
    return AccessionRegistry(config=config, accession_store=accession_store), (
        accession_store
    )


@pytest.fixture
def one_character_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    """Shrink the random blocks to one character, so that a test can use up all 32."""
    monkeypatch.setattr(accession_registry_module, "RANDOM_BLOCK_LENGTH", 1)


def test_fresh_study_pid(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
):
    """A new study gets 'PREFIX.YY.XXX.1' of the current year, its root registered."""
    accession_registry, accession_store = make_registry(config_sub_fixture)

    study_pid = accession_registry.generate_study_accession()

    assert re.fullmatch(STUDY_PID_PATTERN, study_pid)
    _, year, random_block, version = study_pid.split(".")
    assert version == "1"
    assert year == now_as_utc().strftime("%y")
    assert accession_store.get_random_blocks(year=year) == {random_block}


def test_fresh_study_pids_are_unique(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
):
    """Each new study gets its own root."""
    accession_registry, accession_store = make_registry(config_sub_fixture)

    study_pids = {accession_registry.generate_study_accession() for _ in range(50)}

    assert len(study_pids) == 50
    year = now_as_utc().strftime("%y")
    assert len(accession_store.get_random_blocks(year=year)) == 50


@pytest.mark.usefixtures("one_character_blocks")
def test_study_pid_fallback_finds_last_unused_root(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
):
    """When the random draws keep colliding, the fallback finds the one root left."""
    accession_registry, accession_store = make_registry(config_sub_fixture)
    year = now_as_utc().strftime("%y")
    for character in BASE32_ALPHABET[:-1]:
        accession_store.save(year=year, random_block=character)

    study_pid = accession_registry.generate_study_accession()

    assert study_pid == f"{STUDY_PID_PREFIX}.{year}.{BASE32_ALPHABET[-1]}.1"


@pytest.mark.usefixtures("one_character_blocks")
def test_study_pid_exhausted(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
):
    """When every root of the year is taken, minting a study PID fails."""
    accession_registry, accession_store = make_registry(config_sub_fixture)
    year = now_as_utc().strftime("%y")
    for character in BASE32_ALPHABET:
        accession_store.save(year=year, random_block=character)

    with pytest.raises(AccessionRegistry.AccessionGenerationError):
        accession_registry.generate_study_accession()


def test_dataset_pids(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
):
    """Dataset PIDs are '{study_pid}.DS.XXX', never one already used in the study,
    and nothing is registered in the store.
    """
    accession_registry, accession_store = make_registry(config_sub_fixture)
    study_pid = accession_registry.generate_study_accession()
    used_accessions: set[str] = set()

    for _ in range(50):
        dataset_pid = accession_registry.generate_dataset_accession(
            study_pid=study_pid, used_accessions=used_accessions
        )
        assert re.fullmatch(DATASET_PID_PATTERN, dataset_pid)
        assert dataset_pid.startswith(f"{study_pid}.{DATASET_PID_PREFIX}.")
        assert dataset_pid not in used_accessions
        used_accessions.add(dataset_pid)

    year = now_as_utc().strftime("%y")
    assert len(accession_store.get_random_blocks(year=year)) == 1


@pytest.mark.usefixtures("one_character_blocks")
def test_dataset_pids_exhausted(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
):
    """Every dataset PID of the study is found before minting one more fails."""
    accession_registry, _ = make_registry(config_sub_fixture)
    study_pid = "GHGA.26.K.1"
    used_accessions: set[str] = set()

    for _ in BASE32_ALPHABET:
        used_accessions.add(
            accession_registry.generate_dataset_accession(
                study_pid=study_pid, used_accessions=used_accessions
            )
        )

    assert len(used_accessions) == len(BASE32_ALPHABET)
    with pytest.raises(AccessionRegistry.AccessionGenerationError):
        accession_registry.generate_dataset_accession(
            study_pid=study_pid, used_accessions=used_accessions
        )


def test_get_accession_by_class(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
):
    """The study takes the study PID and a dataset a dataset PID. Every other
    resource gets none, since `add_accessions` composes it from the alias.
    """
    accession_registry, _ = make_registry(config_sub_fixture)
    study_pid = "GHGA.26.K7Q.1"

    def get_accession(class_name: str, alias: str) -> str:
        return accession_registry.generate_accession(
            class_name=class_name,
            alias=alias,
            study_pid=study_pid,
            used_accessions=set(),
        )

    assert get_accession("Study", "STUDY_1") == study_pid
    assert get_accession("Dataset", "DS_1").startswith(
        f"{study_pid}.{DATASET_PID_PREFIX}."
    )
    with pytest.raises(AccessionRegistry.AccessionGenerationError):
        get_accession("Sample", "SAMPLE_1")
