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

from ghga_service_commons.utils.utc_dates import now_as_utc
from metldata.accession_registry.accession_registry import (
    BASE32_ALPHABET,
    AccessionRegistry,
)
from metldata.accession_registry.accession_store import AccessionStore
from metldata.config import SubmissionConfig
from tests.fixtures.config import config_sub_fixture  # noqa: F401

STUDY_PID_PATTERN = re.compile(r"^GHGA\.(\d{2})\.([A-Z2-7]{3})\.1$")
DATASET_PID_PATTERN = re.compile(r"^GHGA\.\d{2}\.[A-Z2-7]{3}\.1\.DS\.[A-Z2-7]{3}$")


def make_registry(
    config: SubmissionConfig, **overrides
) -> tuple[AccessionRegistry, AccessionStore]:
    """Build an accession registry and its store from the config with overrides."""
    config = config.model_copy(update=overrides)
    accession_store = AccessionStore(config=config)
    return AccessionRegistry(config=config, accession_store=accession_store), (
        accession_store
    )


def test_fresh_study_pid(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
):
    """A new study gets 'GHGA.YY.XXX.1' of the current year, its root registered."""
    accession_registry, accession_store = make_registry(config_sub_fixture)

    study_pid = accession_registry.get_study_accession()

    match = STUDY_PID_PATTERN.match(study_pid)
    assert match
    assert match.group(1) == now_as_utc().strftime("%y")
    assert accession_store.get_random_blocks(year=match.group(1)) == {match.group(2)}


def test_fresh_study_pids_are_unique(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
):
    """Each new study gets its own root."""
    accession_registry, accession_store = make_registry(config_sub_fixture)

    study_pids = {accession_registry.get_study_accession() for _ in range(50)}

    assert len(study_pids) == 50
    year = now_as_utc().strftime("%y")
    assert len(accession_store.get_random_blocks(year=year)) == 50


def test_legacy_predecessor_starts_fresh_root(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
):
    """A study replacing a legacy study accession starts a fresh lineage."""
    accession_registry, _ = make_registry(config_sub_fixture)

    study_pid = accession_registry.get_study_accession(
        predecessor_pid="GHGAS12345678901234"
    )

    assert STUDY_PID_PATTERN.match(study_pid)


def test_study_pid_predecessor_continues_lineage(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
):
    """A study replacing a study PID keeps its root and increases the version by
    one, registering nothing new.
    """
    accession_registry, accession_store = make_registry(config_sub_fixture)
    first = accession_registry.get_study_accession()
    root = first.removesuffix(".1")

    second = accession_registry.get_study_accession(predecessor_pid=first)
    third = accession_registry.get_study_accession(predecessor_pid=second)

    assert second == f"{root}.2"
    assert third == f"{root}.3"
    _, year, random_block = root.split(".")
    assert accession_store.get_random_blocks(year=year) == {random_block}


@pytest.mark.parametrize(
    "predecessor_pid",
    [
        "GHGAD12345678901234",  # a legacy dataset, not a study
        "GHGA.24.K7Q.0",  # version 0
        "GHGA.24.K18.1",  # '1' and '8' are not base32
        "GHGA.24.K7QQ.1",  # random block too long
        "OTHER.24.K7Q.1",  # wrong prefix
    ],
)
def test_malformed_predecessor_rejected(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
    predecessor_pid: str,
):
    """A predecessor that is neither a legacy study accession nor a study PID is
    rejected.
    """
    accession_registry, _ = make_registry(config_sub_fixture)

    with pytest.raises(AccessionRegistry.InvalidPredecessorError):
        accession_registry.get_study_accession(predecessor_pid=predecessor_pid)


def test_never_minted_predecessor_rejected(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
):
    """A well-formed study PID whose root was never registered is rejected."""
    accession_registry, _ = make_registry(config_sub_fixture)

    with pytest.raises(AccessionRegistry.InvalidPredecessorError):
        accession_registry.get_study_accession(predecessor_pid="GHGA.24.K7Q.3")


def test_study_pid_fallback_finds_last_unused_root(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
):
    """When the random draws keep colliding, the fallback finds the one root left."""
    accession_registry, accession_store = make_registry(
        config_sub_fixture, random_block_length=1
    )
    year = now_as_utc().strftime("%y")
    for character in BASE32_ALPHABET[:-1]:
        accession_store.save(year=year, random_block=character)

    study_pid = accession_registry.get_study_accession()

    assert study_pid == f"GHGA.{year}.{BASE32_ALPHABET[-1]}.1"


def test_study_pid_exhausted(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
):
    """When every root of the year is taken, minting a study PID fails."""
    accession_registry, accession_store = make_registry(
        config_sub_fixture, random_block_length=1
    )
    year = now_as_utc().strftime("%y")
    for character in BASE32_ALPHABET:
        accession_store.save(year=year, random_block=character)

    with pytest.raises(AccessionRegistry.AccessionGenerationError):
        accession_registry.get_study_accession()


def test_dataset_pids(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
):
    """Dataset PIDs are '{study_pid}.DS.XXX', never one already used in the study,
    and nothing is registered in the store.
    """
    accession_registry, accession_store = make_registry(config_sub_fixture)
    study_pid = accession_registry.get_study_accession()
    used_dataset_pids: set[str] = set()

    for _ in range(50):
        dataset_pid = accession_registry.get_dataset_accession(
            study_pid=study_pid, used_dataset_pids=used_dataset_pids
        )
        assert DATASET_PID_PATTERN.match(dataset_pid)
        assert dataset_pid.startswith(f"{study_pid}.DS.")
        assert dataset_pid not in used_dataset_pids
        used_dataset_pids.add(dataset_pid)

    year = now_as_utc().strftime("%y")
    assert len(accession_store.get_random_blocks(year=year)) == 1


def test_dataset_pids_exhausted(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
):
    """Every dataset PID of the study is found before minting one more fails."""
    accession_registry, _ = make_registry(config_sub_fixture, random_block_length=1)
    study_pid = "GHGA.26.K.1"
    used_dataset_pids: set[str] = set()

    for _ in BASE32_ALPHABET:
        used_dataset_pids.add(
            accession_registry.get_dataset_accession(
                study_pid=study_pid, used_dataset_pids=used_dataset_pids
            )
        )

    assert len(used_dataset_pids) == len(BASE32_ALPHABET)
    with pytest.raises(AccessionRegistry.AccessionGenerationError):
        accession_registry.get_dataset_accession(
            study_pid=study_pid, used_dataset_pids=used_dataset_pids
        )


def test_get_accession_by_class(
    config_sub_fixture: SubmissionConfig,  # noqa: F811
):
    """The study takes the study PID, a dataset a dataset PID, and every other
    resource the accession composed from its alias.
    """
    accession_registry, _ = make_registry(config_sub_fixture)
    study_pid = "GHGA.26.K7Q.1"

    def get_accession(class_name: str, alias: str) -> str:
        return accession_registry.get_accession(
            class_name=class_name,
            alias=alias,
            study_pid=study_pid,
            used_accessions=set(),
        )

    assert get_accession("Study", "STUDY_1") == study_pid
    assert get_accession("Dataset", "DS_1").startswith(f"{study_pid}.DS.")
    assert get_accession("Sample", "SAMPLE_1") == f"{study_pid}.SAMPLE_1"
