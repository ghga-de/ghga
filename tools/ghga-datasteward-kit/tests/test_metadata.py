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

"""Metadata related tests"""

import io
import json
import os
import re
import shutil
import sys
from collections.abc import Generator
from functools import partial
from itertools import count
from pathlib import Path

import pytest
import typer

from ghga_datasteward_kit.amendment import amendment, legacy_accessioning
from ghga_datasteward_kit.amendment.amendment import AccessionChanges
from ghga_datasteward_kit.amendment.exceptions import (
    AccessionNotLegacyError,
    AmendmentStatusError,
    StudyAccessionMissingError,
)
from ghga_datasteward_kit.cli.metadata import amend, submit, transform
from metldata.model_utils.anchors import AnchorPoint
from metldata.model_utils.metadata_validator import MetadataValidationError
from metldata.submission_registry.submission_store import SubmissionStore
from tests.fixtures.metadata import (
    AMENDED_METADATA_PATH,
    ARCHIVE_METADATA_CONFIG_PATH,
    ARCHIVE_ORIGINAL_METADATA_PATH,
    ARCHIVE_ORIGINAL_MODEL_PATH,
    DROPPED_METADATA_PATH,
    METADATA_CONFIG_PATH,
    ORIGINAL_METADATA_PATH,
    ORIGINAL_MODEL_PATH,
)


def workdir_factory(original_model_path: Path):
    """Prepare a work directory for the provided model."""

    @pytest.fixture
    def workdir(tmp_path: Path) -> Generator[Path, None, None]:
        """Prepare a work directory for"""
        tmp_path.joinpath("event_store").mkdir()
        tmp_path.joinpath("submission_store").mkdir()
        tmp_path.joinpath("accession_store").touch()
        tmp_path.joinpath("artifact_model").touch()
        shutil.copyfile(original_model_path, tmp_path / "original_model.yaml")
        cwd = os.getcwd()
        os.chdir(tmp_path)
        yield tmp_path
        os.chdir(cwd)

    return workdir


example_workdir = workdir_factory(ORIGINAL_MODEL_PATH)
archive_workdir = workdir_factory(ARCHIVE_ORIGINAL_MODEL_PATH)


def test_happy(example_workdir: Path):
    """Test the 'happy' test case that is expected to run through without errors"""
    submit(
        submission_title="Test Title",
        submission_description="Test Description",
        metadata_path=ORIGINAL_METADATA_PATH,
        config_path=METADATA_CONFIG_PATH,
    )

    transform(config_path=METADATA_CONFIG_PATH)


def test_archive_happy(archive_workdir: Path):
    """Test the 'happy' test case that is expected to run through without errors"""
    submit(
        submission_title="Test Title",
        submission_description="Test Description",
        metadata_path=ARCHIVE_ORIGINAL_METADATA_PATH,
        config_path=ARCHIVE_METADATA_CONFIG_PATH,
    )

    transform(config_path=ARCHIVE_METADATA_CONFIG_PATH)


def submit_original() -> tuple[str, dict[str, dict[str, str]]]:
    """Submit the original metadata and return the submission ID and accession map.

    Must be called from within a work directory fixture, since the test config uses
    paths relative to the current working directory.
    """
    submit(
        submission_title="Test Title",
        submission_description="Test Description",
        metadata_path=ORIGINAL_METADATA_PATH,
        config_path=METADATA_CONFIG_PATH,
    )

    submission_paths = list(Path("submission_store").glob("*.json"))
    assert len(submission_paths) == 1

    submission = json.loads(submission_paths[0].read_text(encoding="utf-8"))
    return submission["id"], submission["accession_map"]


# the flat prefixes for the classes of the test model
TEST_LEGACY_PREFIXES = {
    "Study": "GHGAS",
    "SampleFile": "GHGAF",
    "ExperimentFile": "GHGAF",
    "Dataset": "GHGAD",
    "Sample": "GHGAN",
    "Experiment": "GHGAX",
}


def make_legacy(*, submission_id: str) -> dict[str, dict[str, str]]:
    """Give a stored submission flat accessions, as if it was accessioned before
    study PIDs, and return its new accession map.
    """
    path = Path("submission_store") / f"{submission_id}.json"
    submission = json.loads(path.read_text(encoding="utf-8"))

    flat_accessions = (f"GHGAT{index:014d}" for index in count())
    submission["accession_map"] = {
        anchor: {alias: next(flat_accessions) for alias in accessions}
        for anchor, accessions in submission["accession_map"].items()
    }
    path.write_text(json.dumps(submission), encoding="utf-8")

    return submission["accession_map"]


def submit_legacy() -> tuple[str, dict[str, dict[str, str]]]:
    """Submit the original metadata with flat accessions, as only a submission
    accessioned before study PIDs can be amended, and return the submission ID and
    accession map.

    Must be called from within a work directory fixture, like `submit_original`.
    """
    submission_id, _ = submit_original()
    return submission_id, make_legacy(submission_id=submission_id)


def read_accession_map(*, submission_id: str) -> dict[str, dict[str, str]]:
    """Read the accession map of a stored submission."""
    path = Path("submission_store") / f"{submission_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))["accession_map"]


class _TerminalStdin(io.StringIO):
    """A stdin that claims to be a terminal, so confirmation is reachable."""

    def isatty(self) -> bool:
        return True


def pretend_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the amend command believe it is running interactively.

    Under pytest stdin is not a terminal, and a risky amendment is refused outright
    without one, so a test that exercises the prompt has to say it has one.
    """
    monkeypatch.setattr(sys, "stdin", _TerminalStdin())


@pytest.mark.usefixtures("legacy_amendment")
def test_amend_preserves_accessions(example_workdir: Path):
    """Test that amending a submission with an added file keeps every accession that
    was already assigned, and mints one only for the added alias.
    """
    submission_id, accessions_before = submit_legacy()

    amend(
        submission_id=submission_id,
        metadata_path=AMENDED_METADATA_PATH,
        config_path=METADATA_CONFIG_PATH,
    )

    accessions_after = read_accession_map(submission_id=submission_id)

    for anchor, accessions in accessions_before.items():
        for alias, accession in accessions.items():
            assert accessions_after[anchor][alias] == accession

    assert "test_sample_03_R1" in accessions_after["sample_files"]
    assert "test_sample_03_R1" not in accessions_before["sample_files"]

    # the submission and its source event are replaced, not duplicated:
    assert len(list(Path("submission_store").glob("*.json"))) == 1
    assert len(list(Path("event_store/source_events").glob("*.json"))) == 1

    transform(config_path=METADATA_CONFIG_PATH)


@pytest.mark.usefixtures("legacy_amendment")
def test_amend_dropped_alias_needs_confirmation(
    example_workdir: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    """Test that an amendment dropping an alias is refused unless confirmed, and that
    refusing it leaves the submission untouched and reports no success.
    """
    submission_id, _ = submit_legacy()
    submission_path = Path("submission_store") / f"{submission_id}.json"
    content_before = submission_path.read_bytes()

    pretend_terminal(monkeypatch)
    monkeypatch.setattr(typer, "confirm", lambda *args, **kwargs: False)

    with pytest.raises(typer.Abort):
        amend(
            submission_id=submission_id,
            metadata_path=DROPPED_METADATA_PATH,
            config_path=METADATA_CONFIG_PATH,
        )

    assert submission_path.read_bytes() == content_before
    assert "amended." not in capsys.readouterr().out


@pytest.mark.usefixtures("legacy_amendment")
def test_amend_dropped_alias_confirmed(
    example_workdir: Path, monkeypatch: pytest.MonkeyPatch
):
    """Test that a confirmed amendment drops the accession of a removed alias and
    keeps all others.
    """
    submission_id, accessions_before = submit_legacy()

    pretend_terminal(monkeypatch)
    monkeypatch.setattr(typer, "confirm", lambda *args, **kwargs: True)

    amend(
        submission_id=submission_id,
        metadata_path=DROPPED_METADATA_PATH,
        config_path=METADATA_CONFIG_PATH,
    )

    accessions_after = read_accession_map(submission_id=submission_id)
    assert "test_sample_01_R2" not in accessions_after["sample_files"]
    assert (
        accessions_after["sample_files"]["test_sample_01_R1"]
        == accessions_before["sample_files"]["test_sample_01_R1"]
    )


@pytest.mark.parametrize("keep_anchor", [False, True], ids=["no_anchor", "empty"])
def test_amend_without_study_accession(example_workdir: Path, keep_anchor: bool):
    """Test that a stored accession map without a study accession is refused with an
    error naming the submission, whether the study's anchor is missing or empty.
    """
    submission_id, _ = submit_original()
    path = Path("submission_store") / f"{submission_id}.json"
    submission = json.loads(path.read_text(encoding="utf-8"))
    accession_map = submission["accession_map"]
    study_anchor = next(
        anchor
        for anchor, accessions in accession_map.items()
        if any(
            re.fullmatch(r"GHGA\.\d{2}\.[A-Z2-7]+\.1", accession)
            for accession in accessions.values()
        )
    )
    if keep_anchor:
        accession_map[study_anchor] = {}
    else:
        del accession_map[study_anchor]
    path.write_text(json.dumps(submission), encoding="utf-8")

    with pytest.raises(StudyAccessionMissingError, match=submission_id):
        amend(
            submission_id=submission_id,
            metadata_path=AMENDED_METADATA_PATH,
            config_path=METADATA_CONFIG_PATH,
        )


def test_amend_refuses_study_pid_submission(
    example_workdir: Path, capsys: pytest.CaptureFixture[str]
):
    """Test that a submission whose study has a study PID is refused, naming the
    submission, and that nothing is written or minted and no success is reported.
    """
    submission_id, _ = submit_original()
    submission_path = Path("submission_store") / f"{submission_id}.json"
    content_before = submission_path.read_bytes()
    accession_store_before = Path("accession_store").read_text(encoding="utf-8")

    with pytest.raises(AccessionNotLegacyError, match=submission_id):
        amend(
            submission_id=submission_id,
            metadata_path=AMENDED_METADATA_PATH,
            config_path=METADATA_CONFIG_PATH,
        )

    assert submission_path.read_bytes() == content_before
    assert Path("accession_store").read_text(encoding="utf-8") == accession_store_before
    assert "amended." not in capsys.readouterr().out


def test_amend_unknown_submission(example_workdir: Path):
    """Test that amending a submission that does not exist is an error."""
    submit_original()

    with pytest.raises(SubmissionStore.SubmissionDoesNotExistError):
        amend(
            submission_id="does-not-exist",
            metadata_path=AMENDED_METADATA_PATH,
            config_path=METADATA_CONFIG_PATH,
        )


@pytest.mark.usefixtures("legacy_amendment")
def test_amend_mints_nothing_when_aborted(
    example_workdir: Path, monkeypatch: pytest.MonkeyPatch
):
    """Test that planning an amendment does not consume accessions, so declining one
    leaves the accession store untouched.
    """
    submission_id, _ = submit_legacy()
    accession_store_before = Path("accession_store").read_text(encoding="utf-8")

    pretend_terminal(monkeypatch)
    monkeypatch.setattr(typer, "confirm", lambda *args, **kwargs: False)

    with pytest.raises(typer.Abort):
        amend(
            submission_id=submission_id,
            metadata_path=DROPPED_METADATA_PATH,
            config_path=METADATA_CONFIG_PATH,
        )

    assert Path("accession_store").read_text(encoding="utf-8") == accession_store_before


def test_needs_confirmation():
    """Test which amendments are considered risky enough to confirm."""
    pure_addition = AccessionChanges(
        preserved={"files": {"a": "GHGAF1"}}, new_aliases={"files": ["b"]}
    )
    assert not amendment.needs_confirmation(changes=pure_addition)

    with_drop = AccessionChanges(
        preserved={"files": {"a": "GHGAF1"}}, dropped={"files": {"b": "GHGAF2"}}
    )
    assert amendment.needs_confirmation(changes=with_drop)

    nothing_preserved = AccessionChanges(new_aliases={"files": ["a"]})
    assert amendment.needs_confirmation(changes=nothing_preserved)


ANCHOR_POINTS = {
    "Class1": AnchorPoint(
        root_slot="class1_anchor", target_class="Class1", identifier_slot="alias"
    ),
    "Class2": AnchorPoint(
        root_slot="class2_anchor", target_class="Class2", identifier_slot="alias"
    ),
}


def test_plan_accession_changes():
    """Test planning the accession changes an amendment would cause.

    Covers an alias that keeps its accession, an alias that needs a new one, an alias
    that loses its accession, and a whole anchor that disappears from the content.
    """
    changes = amendment.find_accession_changes(
        content={
            "class1_anchor": [{"alias": "kept"}, {"alias": "added"}],
        },
        existing_accession_map={
            "class1_anchor": {"kept": "ACC1", "gone": "ACC2"},
            "class2_anchor": {"orphan": "ACC3"},
        },
        anchor_points_by_target=ANCHOR_POINTS,
        class_names=ANCHOR_POINTS.keys(),
    )

    assert changes.preserved == {"class1_anchor": {"kept": "ACC1"}}
    assert changes.new_aliases == {"class1_anchor": ["added"]}
    assert changes.dropped == {
        "class1_anchor": {"gone": "ACC2"},
        "class2_anchor": {"orphan": "ACC3"},
    }
    assert changes.preserved_count == 1
    assert changes.new_alias_count == 1
    assert changes.dropped_count == 2
    assert not changes.is_lossless


def test_plan_accession_changes_pure_addition():
    """Test that adding a resource preserves every existing accession and drops none,
    which is the case the amend command exists for.
    """
    changes = amendment.find_accession_changes(
        content={"class1_anchor": [{"alias": "old"}, {"alias": "new"}]},
        existing_accession_map={"class1_anchor": {"old": "ACC1"}},
        anchor_points_by_target=ANCHOR_POINTS,
        class_names=ANCHOR_POINTS.keys(),
    )

    assert changes.preserved == {"class1_anchor": {"old": "ACC1"}}
    assert changes.new_aliases == {"class1_anchor": ["new"]}
    assert changes.is_lossless


def test_amend_requires_completed_submission(example_workdir: Path):
    """Test that a submission still pending cannot be amended.

    `submit` always completes a submission, so this only happens if a previous run was
    interrupted between providing content and completing it.
    """
    submission_id, _ = submit_original()

    # drop the completion, leaving the submission pending
    submission_path = Path("submission_store") / f"{submission_id}.json"
    submission = json.loads(submission_path.read_text(encoding="utf-8"))
    submission["status_history"] = submission["status_history"][:1]
    assert submission["status_history"][0]["new_status"] == "pending"
    submission_path.write_text(json.dumps(submission), encoding="utf-8")

    with pytest.raises(AmendmentStatusError):
        amend(
            submission_id=submission_id,
            metadata_path=AMENDED_METADATA_PATH,
            config_path=METADATA_CONFIG_PATH,
        )


@pytest.mark.usefixtures("legacy_amendment")
def test_amend_refuses_risky_amendment_without_a_terminal(
    example_workdir: Path, monkeypatch: pytest.MonkeyPatch
):
    """Test that a risky amendment is refused when stdin is not a terminal.

    `typer.confirm` reads with `input()` and never checks for a terminal, so a piped
    `y` would otherwise answer for someone who never saw the report. The prompt is the
    only safeguard against dropping accessions, so it must not be answerable that way.
    """
    submission_id, _ = submit_legacy()
    submission_path = Path("submission_store") / f"{submission_id}.json"
    content_before = submission_path.read_bytes()
    accession_store_before = Path("accession_store").read_text(encoding="utf-8")

    # a terminal is never pretended here, and answering must not even be attempted
    def fail_if_asked(*args, **kwargs):
        raise AssertionError("confirmation must not be read from a non-terminal stdin")

    monkeypatch.setattr(typer, "confirm", fail_if_asked)

    with pytest.raises(typer.Abort):
        amend(
            submission_id=submission_id,
            metadata_path=DROPPED_METADATA_PATH,
            config_path=METADATA_CONFIG_PATH,
        )

    assert submission_path.read_bytes() == content_before
    assert Path("accession_store").read_text(encoding="utf-8") == accession_store_before


# the file classes of the test model, in place of the GHGA model's
TEST_FILE_CLASS_NAMES = ("SampleFile", "ExperimentFile")


@pytest.fixture
def legacy_amendment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Let an amendment run on the test model: mint flat accessions with prefixes for
    its classes, and compare its file classes.
    """
    monkeypatch.setattr(legacy_accessioning, "LEGACY_PREFIXES", TEST_LEGACY_PREFIXES)
    monkeypatch.setattr(
        amendment,
        "find_accession_changes",
        partial(amendment.find_accession_changes, class_names=TEST_FILE_CLASS_NAMES),
    )


@pytest.mark.usefixtures("legacy_amendment")
def test_amend_mints_flat_accession(
    example_workdir: Path, capsys: pytest.CaptureFixture[str]
):
    """Test that an amendment mints a flat accession for a new alias, 'GHGAF' and 14
    digits for a file, registers it as legacy in the accession store, and reports
    its success last.
    """
    submission_id, _ = submit_legacy()

    amend(
        submission_id=submission_id,
        metadata_path=AMENDED_METADATA_PATH,
        config_path=METADATA_CONFIG_PATH,
    )

    output_lines = capsys.readouterr().out.splitlines()
    assert output_lines[-1] == f"Submission {submission_id} amended."

    accessions_after = read_accession_map(submission_id=submission_id)
    minted = accessions_after["sample_files"]["test_sample_03_R1"]
    assert re.fullmatch(r"GHGAF\d{14}", minted)

    accession_store = json.loads(Path("accession_store").read_text(encoding="utf-8"))
    assert accession_store["legacy"] == [minted]


@pytest.mark.usefixtures("legacy_amendment")
def test_amend_class_without_flat_prefix(
    example_workdir: Path, monkeypatch: pytest.MonkeyPatch
):
    """Test that a new resource of a class without a flat prefix is refused with an
    error naming the class, and that the accession map stays unchanged.
    """
    submission_id, accessions_before = submit_legacy()
    prefixes = {
        class_name: prefix
        for class_name, prefix in TEST_LEGACY_PREFIXES.items()
        if class_name != "SampleFile"
    }
    monkeypatch.setattr(legacy_accessioning, "LEGACY_PREFIXES", prefixes)

    with pytest.raises(
        legacy_accessioning.LegacyAccessionRegistry.AccessionGenerationError,
        match="'SampleFile'",
    ):
        amend(
            submission_id=submission_id,
            metadata_path=AMENDED_METADATA_PATH,
            config_path=METADATA_CONFIG_PATH,
        )

    assert read_accession_map(submission_id=submission_id) == accessions_before


@pytest.mark.usefixtures("legacy_amendment")
def test_amend_renamed_study_keeps_its_accession(example_workdir: Path):
    """Test that a study whose alias changed keeps its accession under the new alias,
    since a new alias does not make it a new study.
    """
    submission_id, accessions_before = submit_legacy()
    renamed_metadata_path = Path("renamed_metadata.yaml")
    renamed_metadata_path.write_text(
        ORIGINAL_METADATA_PATH.read_text(encoding="utf-8").replace(
            "alias: test_study", "alias: renamed_study"
        ),
        encoding="utf-8",
    )

    amendment.amend_metadata_from_path(
        submission_id=submission_id,
        metadata_path=renamed_metadata_path,
        config_path=METADATA_CONFIG_PATH,
    )

    accessions_after = read_accession_map(submission_id=submission_id)
    assert accessions_after["studies"] == {
        "renamed_study": accessions_before["studies"]["test_study"]
    }


LEGACY_ANCHORS = {
    "C": AnchorPoint(root_slot="files", target_class="C", identifier_slot="alias"),
    "D": AnchorPoint(root_slot="others", target_class="D", identifier_slot="alias"),
}


def test_check_alias_uniqueness_per_class():
    """Test that an alias repeated within a class is rejected, and one shared across
    classes is not, since flat accessions hold no alias.
    """
    legacy_accessioning.check_alias_uniqueness_per_class(
        content={"files": [{"alias": "a"}], "others": [{"alias": "a"}]},
        anchor_points_by_target=LEGACY_ANCHORS,
    )

    with pytest.raises(
        MetadataValidationError, match=r"value 'a': .* 2 entities of the class 'C'"
    ):
        legacy_accessioning.check_alias_uniqueness_per_class(
            content={"files": [{"alias": "a"}, {"alias": "a"}, {"alias": "b"}]},
            anchor_points_by_target=LEGACY_ANCHORS,
        )
