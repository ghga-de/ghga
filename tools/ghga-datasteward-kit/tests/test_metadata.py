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
from pathlib import Path

import pytest
import typer

from ghga_datasteward_kit import study_pid_reservation
from ghga_datasteward_kit.amendment import amendment, legacy_accessioning
from ghga_datasteward_kit.amendment.amendment import AccessionChanges
from ghga_datasteward_kit.amendment.exceptions import (
    AccessionNotLegacyError,
    AmendmentStatusError,
    StudyAccessionInUseError,
    StudyAccessionMissingError,
    StudyAccessionNotFlatError,
)
from ghga_datasteward_kit.cli.metadata import amend, list_pending, submit, transform
from ghga_datasteward_kit.cli.metadata import (
    reserve_study_pid as reserve_study_pid_command,
)
from ghga_datasteward_kit.cli.metadata import submit_legacy as submit_legacy_command
from ghga_datasteward_kit.cli.metadata import submit_pending as submit_pending_command
from ghga_service_commons.utils.accessions import STUDY_PID_PATTERN
from metldata.model_utils.anchors import AnchorPoint
from metldata.model_utils.metadata_validator import MetadataValidationError
from metldata.submission_registry.models import Submission
from metldata.submission_registry.submission_registry import SubmissionRegistry
from metldata.submission_registry.submission_store import SubmissionStore
from tests.fixtures.metadata import (
    AMENDED_METADATA_PATH,
    ARCHIVE_METADATA_CONFIG_PATH,
    ARCHIVE_ORIGINAL_METADATA_PATH,
    ARCHIVE_ORIGINAL_MODEL_PATH,
    DROPPED_METADATA_PATH,
    LEGACY_SUBMISSION_ID,
    LEGACY_SUBMISSION_PATH,
    METADATA_CONFIG_PATH,
    ORIGINAL_METADATA_PATH,
    ORIGINAL_MODEL_PATH,
)


def workdir_factory(original_model_path: Path):
    """Prepare a work directory for the provided model."""

    @pytest.fixture
    def workdir(tmp_path: Path) -> Generator[Path]:
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


def read_submission(*, submission_id: str) -> dict:
    """Read a stored submission."""
    path = Path("submission_store") / f"{submission_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def read_accession_map(*, submission_id: str) -> dict[str, dict[str, str]]:
    """Read the accession map of a stored submission."""
    return read_submission(submission_id=submission_id)["accession_map"]


def submit_legacy() -> tuple[str, dict[str, dict[str, str]]]:
    """Store a completed submission accessioned before study PIDs, as only such a
    submission can be amended, and return its ID and accession map.

    Copied from a fixture rather than submitted, since `submit` mints study PIDs
    only. Must be called from within a work directory fixture, like
    `submit_original`.
    """
    shutil.copyfile(
        LEGACY_SUBMISSION_PATH,
        Path("submission_store") / f"{LEGACY_SUBMISSION_ID}.json",
    )
    return LEGACY_SUBMISSION_ID, read_accession_map(submission_id=LEGACY_SUBMISSION_ID)


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

    minted = {
        (anchor, alias)
        for anchor, accessions in accessions_after.items()
        for alias in accessions
        if alias not in accessions_before.get(anchor, {})
    }
    assert minted == {("sample_files", "test_sample_03_R1")}, (
        "amend minted accessions for aliases other than the added one; if the"
        + " fixtures changed, legacy_submission.json may no longer hold the content"
        + " of original_metadata.yaml"
    )

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
            re.fullmatch(STUDY_PID_PATTERN, accession)
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


# a flat study accession handed out before the study's metadata arrived
PROMISED_STUDY_ACCESSION = "GHGAS00000000000001"

# the flat prefix per anchor of the test model, the study aside
TEST_LEGACY_PREFIXES_BY_ANCHOR = {
    "sample_files": "GHGAF",
    "experiment_files": "GHGAF",
    "datasets": "GHGAD",
    "samples": "GHGAN",
    "experiments": "GHGAX",
}


def submit_promised(
    *,
    metadata_path: Path = ORIGINAL_METADATA_PATH,
    study_accession: str = PROMISED_STUDY_ACCESSION,
) -> None:
    """Run `submit-legacy` on the given metadata with the given study accession.

    Must be called from within a work directory fixture, like `submit_original`.
    """
    submit_legacy_command(
        submission_title="Test Title",
        submission_description="Test Description",
        study_accession=study_accession,
        metadata_path=metadata_path,
        config_path=METADATA_CONFIG_PATH,
    )


def read_single_submission() -> dict:
    """Read the one submission in the submission store."""
    submission_paths = list(Path("submission_store").glob("*.json"))
    assert len(submission_paths) == 1
    return json.loads(submission_paths[0].read_text(encoding="utf-8"))


def write_changed_metadata(*, old: str, new: str) -> Path:
    """Write the original metadata with one text replaced, and return its path."""
    original = ORIGINAL_METADATA_PATH.read_text(encoding="utf-8")
    assert old in original
    path = Path("changed_metadata.yaml")
    path.write_text(original.replace(old, new), encoding="utf-8")
    return path


def failing_insert_new(self: SubmissionStore, *, submission: Submission) -> None:
    """Stand in for a submission store that cannot write."""
    raise OSError("cannot write the submission")


def assert_nothing_submitted() -> None:
    """Check that no submission and no source event were written."""
    assert not list(Path("submission_store").glob("*.json"))
    assert not list(Path("event_store").rglob("*.json"))


@pytest.mark.usefixtures("legacy_amendment")
def test_submit_legacy_mints_flat_accessions(
    example_workdir: Path, capsys: pytest.CaptureFixture[str]
):
    """Test that `submit-legacy` gives the study the promised accession and every
    other resource a flat one, registers all of them in the accession store, stores
    the submission as completed and reports its ID last.
    """
    submit_promised()

    submission = read_single_submission()
    accession_map = submission["accession_map"]

    output_lines = capsys.readouterr().out.splitlines()
    assert output_lines[-1] == f"Submission {submission['id']} submitted."

    assert accession_map["studies"] == {"test_study": PROMISED_STUDY_ACCESSION}

    # a flat map holds every class, and an accession for each of its aliases
    assert set(accession_map) == set(submission["content"])
    for anchor, prefix in TEST_LEGACY_PREFIXES_BY_ANCHOR.items():
        aliases = {resource["alias"] for resource in submission["content"][anchor]}
        assert set(accession_map[anchor]) == aliases
        for accession in accession_map[anchor].values():
            assert re.fullmatch(rf"{prefix}\d{{14}}", accession)

    all_accessions = [
        accession
        for accessions in accession_map.values()
        for accession in accessions.values()
    ]
    accession_store = json.loads(Path("accession_store").read_text(encoding="utf-8"))
    assert sorted(accession_store["legacy"]) == sorted(all_accessions)
    assert accession_store["years"] == {}

    assert submission["status_history"][-1]["new_status"] == "completed"
    assert len(list(Path("event_store/source_events").glob("*.json"))) == 1

    transform(config_path=METADATA_CONFIG_PATH)


@pytest.mark.usefixtures("legacy_amendment")
def test_submit_legacy_can_be_amended(example_workdir: Path):
    """Test that a submission from `submit-legacy` is amended like one from before
    study PIDs: an added file gets an accession and all others are kept.
    """
    submit_promised()
    submission = read_single_submission()

    amend(
        submission_id=submission["id"],
        metadata_path=AMENDED_METADATA_PATH,
        config_path=METADATA_CONFIG_PATH,
    )

    accessions_after = read_accession_map(submission_id=submission["id"])
    for anchor, accessions in submission["accession_map"].items():
        for alias, accession in accessions.items():
            assert accessions_after[anchor][alias] == accession
    assert re.fullmatch(
        r"GHGAF\d{14}", accessions_after["sample_files"]["test_sample_03_R1"]
    )


@pytest.mark.usefixtures("legacy_amendment")
@pytest.mark.parametrize(
    "study_accession",
    [
        "GHGA.26.ABC.1",
        "GHGAS123",
        "ghgas00000000000001",
        "GHGAS000000000000012",
        "GHGAF00000000000001",
    ],
    ids=["study_pid", "too_short", "lower_case", "too_long", "other_class"],
)
def test_submit_legacy_refuses_non_flat_accession(
    example_workdir: Path, study_accession: str
):
    """Test that a study accession that is not a flat one is refused by name, before
    anything is minted or written.
    """
    with pytest.raises(StudyAccessionNotFlatError, match=re.escape(study_accession)):
        submit_promised(study_accession=study_accession)

    assert_nothing_submitted()
    assert Path("accession_store").read_text(encoding="utf-8") == ""


@pytest.mark.usefixtures("legacy_amendment")
def test_submit_legacy_refuses_accession_of_stored_submission(example_workdir: Path):
    """Test that a study accession a stored submission already has is refused, even
    when it is missing from the accession store, so a second run adds no second
    submission and mints nothing.
    """
    submit_promised()
    submission_id = read_single_submission()["id"]

    # as if registering the study accession had failed after the submission was written
    accession_store = json.loads(Path("accession_store").read_text(encoding="utf-8"))
    accession_store["legacy"].remove(PROMISED_STUDY_ACCESSION)
    Path("accession_store").write_text(json.dumps(accession_store), encoding="utf-8")
    accession_store_before = Path("accession_store").read_text(encoding="utf-8")

    with pytest.raises(StudyAccessionInUseError, match=submission_id):
        submit_promised()

    read_single_submission()
    assert Path("accession_store").read_text(encoding="utf-8") == accession_store_before


@pytest.mark.usefixtures("legacy_amendment")
def test_submit_legacy_accepts_accession_entered_by_hand(example_workdir: Path):
    """Test that a study accession already in the accession store, but not used by
    any submission, is accepted and stays registered once.
    """
    Path("accession_store").write_text(
        json.dumps({"legacy": [PROMISED_STUDY_ACCESSION], "years": {}}),
        encoding="utf-8",
    )

    submit_promised()

    assert read_single_submission()["accession_map"]["studies"] == {
        "test_study": PROMISED_STUDY_ACCESSION
    }
    accession_store = json.loads(Path("accession_store").read_text(encoding="utf-8"))
    assert accession_store["legacy"].count(PROMISED_STUDY_ACCESSION) == 1


@pytest.mark.usefixtures("legacy_amendment")
def test_submit_legacy_alias_repeated_in_class(example_workdir: Path):
    """Test that an alias used twice within one class is refused before anything is
    minted, and that the study accession is still free for the corrected metadata.
    """
    metadata_path = write_changed_metadata(
        old="  - alias: test_sample_02\n", new="  - alias: test_sample_01\n"
    )

    with pytest.raises(MetadataValidationError, match="test_sample_01"):
        submit_promised(metadata_path=metadata_path)

    assert_nothing_submitted()
    assert Path("accession_store").read_text(encoding="utf-8") == ""

    submit_promised()
    assert read_single_submission()["accession_map"]["studies"] == {
        "test_study": PROMISED_STUDY_ACCESSION
    }


@pytest.mark.usefixtures("legacy_amendment")
def test_submit_legacy_failed_write_keeps_accession_free(
    example_workdir: Path, monkeypatch: pytest.MonkeyPatch
):
    """Test that a run that cannot write the submission does not register the study
    accession, and that the next run with the same accession goes through.
    """
    with monkeypatch.context() as patch:
        patch.setattr(SubmissionStore, "insert_new", failing_insert_new)
        with pytest.raises(OSError, match="cannot write the submission"):
            submit_promised()

    accession_store = json.loads(Path("accession_store").read_text(encoding="utf-8"))
    assert PROMISED_STUDY_ACCESSION not in accession_store["legacy"]

    submit_promised()
    assert read_single_submission()["accession_map"]["studies"] == {
        "test_study": PROMISED_STUDY_ACCESSION
    }


@pytest.mark.usefixtures("legacy_amendment")
def test_submit_legacy_alias_shared_across_classes(example_workdir: Path):
    """Test that the same alias in two classes is accepted and gets two accessions,
    since a flat accession does not contain the alias.
    """
    metadata_path = write_changed_metadata(
        old="test_experiment_01", new="test_sample_01"
    )

    submit_promised(metadata_path=metadata_path)

    accession_map = read_single_submission()["accession_map"]
    assert (
        accession_map["samples"]["test_sample_01"]
        != accession_map["experiments"]["test_sample_01"]
    )


@pytest.mark.usefixtures("legacy_amendment")
def test_submit_legacy_class_without_flat_prefix(
    example_workdir: Path, monkeypatch: pytest.MonkeyPatch
):
    """Test that a class without a flat prefix is refused by name before anything is
    minted, with nothing submitted and the accession store untouched.
    """
    prefixes = {
        class_name: prefix
        for class_name, prefix in TEST_LEGACY_PREFIXES.items()
        if class_name != "Experiment"
    }
    monkeypatch.setattr(legacy_accessioning, "LEGACY_PREFIXES", prefixes)

    with pytest.raises(
        legacy_accessioning.LegacyAccessionRegistry.AccessionGenerationError,
        match="'Experiment'",
    ):
        submit_promised()

    assert_nothing_submitted()
    assert Path("accession_store").read_text(encoding="utf-8") == ""


INTERNAL_NAME = "Internal Name"


def reserve() -> tuple[str, str]:
    """Reserve a study PID and return the submission ID and the PID.

    Must be called from within a work directory fixture, like `submit_original`.
    """
    return study_pid_reservation.reserve_study_pid_from_path(
        submission_title=INTERNAL_NAME,
        submission_description=None,
        config_path=METADATA_CONFIG_PATH,
    )


def submit_reserved(
    *,
    submission_id: str,
    study_pid: str,
    metadata_path: Path = ORIGINAL_METADATA_PATH,
) -> None:
    """Run `submit-pending` on the given submission with the given study PID."""
    submit_pending_command(
        submission_id=submission_id,
        study_pid=study_pid,
        submission_title="Test Title",
        submission_description="Test Description",
        metadata_path=metadata_path,
        config_path=METADATA_CONFIG_PATH,
    )


@pytest.fixture
def confirm_submit_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    """Answer the question of `submit-pending` with yes, from a pretended terminal."""
    pretend_terminal(monkeypatch)
    monkeypatch.setattr(typer, "confirm", lambda *args, **kwargs: True)


def failing_complete_submission(self: SubmissionRegistry, *, id_: str) -> None:
    """Stand in for a run that stops before the submission is completed."""
    raise OSError("stopped before completing")


def test_list_pending(example_workdir: Path, capsys: pytest.CaptureFixture[str]):
    """Test that `list-pending` says so when nothing is pending, and otherwise prints
    the study PID, the submission ID and the title of each pending submission.
    """
    list_pending(config_path=METADATA_CONFIG_PATH)
    assert capsys.readouterr().out.splitlines() == ["No pending submissions."]

    reservations = sorted([reserve(), reserve()])

    list_pending(config_path=METADATA_CONFIG_PATH)
    assert capsys.readouterr().out.splitlines() == [
        f"{study_pid}  {submission_id}  {INTERNAL_NAME}"
        for submission_id, study_pid in reservations
    ]


def test_reserve_study_pid(example_workdir: Path, capsys: pytest.CaptureFixture[str]):
    """Test that `reserve-study-pid` reports the reserved study PID and the ID of the
    submission that holds it.
    """
    reserve_study_pid_command(
        submission_title=INTERNAL_NAME,
        submission_description=None,
        config_path=METADATA_CONFIG_PATH,
    )

    submission = read_single_submission()
    study_pid = next(iter(submission["accession_map"]["studies"].values()))
    assert re.fullmatch(STUDY_PID_PATTERN, study_pid)
    assert capsys.readouterr().out.splitlines()[-1] == (
        f"Study PID {study_pid} reserved in submission {submission['id']}."
    )


@pytest.mark.usefixtures("confirm_submit_pending")
def test_submit_pending_keeps_reserved_pid(
    example_workdir: Path, capsys: pytest.CaptureFixture[str]
):
    """Test that `submit-pending` files the reserved PID under the real study alias,
    derives the dataset PIDs from it, replaces the internal name with the title,
    completes the submission and reports the internal name.
    """
    submission_id, study_pid = reserve()

    submit_reserved(submission_id=submission_id, study_pid=study_pid)

    submission = read_single_submission()
    assert submission["accession_map"]["studies"] == {"test_study": study_pid}
    dataset_pids = submission["accession_map"]["datasets"].values()
    assert dataset_pids
    assert all(pid.startswith(f"{study_pid}.DS.") for pid in dataset_pids)
    assert submission["title"] == "Test Title"
    assert submission["description"] == "Test Description"
    assert submission["status_history"][-1]["new_status"] == "completed"
    assert capsys.readouterr().out.splitlines()[-1] == (
        f"Submission {submission_id} ('{INTERNAL_NAME}') submitted."
    )

    transform(config_path=METADATA_CONFIG_PATH)


def test_submit_pending_refuses_mismatched_pid(
    example_workdir: Path, capsys: pytest.CaptureFixture[str]
):
    """Test that the ID of one reservation with the PID of another is refused with a
    plain message before anything is written.
    """
    submission_id, _ = reserve()
    _, other_study_pid = reserve()
    submission_before = read_submission(submission_id=submission_id)

    with pytest.raises(typer.Abort):
        submit_reserved(submission_id=submission_id, study_pid=other_study_pid)

    assert capsys.readouterr().out.splitlines()[-1] == str(
        SubmissionRegistry.StudyPidMismatchError(
            submission_id=submission_id, study_pid=other_study_pid
        )
    )
    assert read_submission(submission_id=submission_id) == submission_before
    assert not list(Path("event_store").rglob("*.json"))


def _decline(*args, **kwargs) -> bool:
    return False


def _fail_if_asked(*args, **kwargs) -> bool:
    raise AssertionError("confirmation must not be read from a non-terminal stdin")


@pytest.mark.parametrize(
    "terminal, confirm",
    [(True, _decline), (False, _fail_if_asked)],
    ids=["declined", "no_terminal"],
)
def test_submit_pending_unconfirmed_writes_nothing(
    terminal: bool,
    confirm,
    example_workdir: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    """Test that metadata is not submitted unless the user confirms it in a terminal,
    and that the submission is then left as it was.
    """
    submission_id, study_pid = reserve()
    submission_before = read_submission(submission_id=submission_id)
    if terminal:
        pretend_terminal(monkeypatch)
    monkeypatch.setattr(typer, "confirm", confirm)

    with pytest.raises(typer.Abort):
        submit_reserved(submission_id=submission_id, study_pid=study_pid)

    output = capsys.readouterr().out
    assert f"is titled '{INTERNAL_NAME}'." in output
    assert output.splitlines()[-1] == "Nothing was submitted."
    assert read_submission(submission_id=submission_id) == submission_before


@pytest.mark.usefixtures("confirm_submit_pending")
def test_submit_pending_invalid_metadata_keeps_reservation(example_workdir: Path):
    """Test that metadata failing validation leaves the reservation as it was, the
    internal name included.
    """
    submission_id, study_pid = reserve()
    submission_before = read_submission(submission_id=submission_id)
    metadata_path = write_changed_metadata(
        old="  - alias: test_sample_02\n", new="  - alias: test_sample_01\n"
    )

    with pytest.raises(MetadataValidationError, match="test_sample_01"):
        submit_reserved(
            submission_id=submission_id,
            study_pid=study_pid,
            metadata_path=metadata_path,
        )

    assert read_submission(submission_id=submission_id) == submission_before


@pytest.mark.usefixtures("confirm_submit_pending")
def test_submit_pending_rerun_after_stop_before_completion(
    example_workdir: Path, monkeypatch: pytest.MonkeyPatch
):
    """Test that a run that stopped after storing the metadata but before completing
    the submission can be repeated, keeping every PID it minted.
    """
    submission_id, study_pid = reserve()

    with monkeypatch.context() as patch:
        patch.setattr(
            SubmissionRegistry, "complete_submission", failing_complete_submission
        )
        with pytest.raises(OSError, match="stopped before completing"):
            submit_reserved(submission_id=submission_id, study_pid=study_pid)

    stopped = read_submission(submission_id=submission_id)
    assert stopped["status_history"][-1]["new_status"] == "pending"

    submit_reserved(submission_id=submission_id, study_pid=study_pid)

    submission = read_submission(submission_id=submission_id)
    assert submission["accession_map"] == stopped["accession_map"]
    assert submission["status_history"][-1]["new_status"] == "completed"
