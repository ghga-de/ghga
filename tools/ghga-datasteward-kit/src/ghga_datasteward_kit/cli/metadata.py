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

"""Metadata related CLI"""

import logging
import sys
from pathlib import Path

import typer

from ghga_datasteward_kit import metadata, study_pid_reservation
from ghga_datasteward_kit.amendment import amendment, legacy_submission
from ghga_datasteward_kit.amendment.amendment import AccessionChanges
from ghga_datasteward_kit.amendment.exceptions import AmendmentAbortedError
from ghga_transpiler.cli import transpile

cli = typer.Typer(no_args_is_help=True)

cli.command(no_args_is_help=True)(transpile)


@cli.command(no_args_is_help=True)
def submit(
    submission_title: str = typer.Option(..., help="The title of the submission."),
    submission_description: str = typer.Option(
        ..., help="The description of the submission."
    ),
    metadata_path: Path = typer.Option(
        ...,
        help="The path to the metadata JSON file.",
        exists=True,
        dir_okay=False,
        file_okay=True,
        readable=True,
    ),
    config_path: Path = typer.Option(
        ...,
        help="Path to a config YAML.",
        exists=True,
        file_okay=True,
        dir_okay=True,
        readable=True,
    ),
):
    """Submit metadata to local submission registry (no upload takes place)."""
    logging.basicConfig(level=logging.CRITICAL)
    metadata.submit_metadata_from_path(
        submission_title=submission_title,
        submission_description=submission_description,
        metadata_path=metadata_path,
        config_path=config_path,
    )


@cli.command(no_args_is_help=True)
def submit_legacy(
    submission_title: str = typer.Option(..., help="The title of the submission."),
    submission_description: str = typer.Option(
        ..., help="The description of the submission."
    ),
    study_accession: str = typer.Option(
        ...,
        help="The flat accession pre-assigned to the study: 'GHGAS' and 14 digits.",
    ),
    metadata_path: Path = typer.Option(
        ...,
        help="The path to the metadata JSON file.",
        exists=True,
        dir_okay=False,
        file_okay=True,
        readable=True,
    ),
    config_path: Path = typer.Option(
        ...,
        help="Path to a config YAML.",
        exists=True,
        file_okay=True,
        dir_okay=True,
        readable=True,
    ),
):
    """Submit metadata for a study that was promised a flat accession.

    Use this instead of 'submit' when the study's accession was handed out under the
    flat scheme before its metadata arrived: the study gets that accession, and every
    other resource gets a new flat one instead of one derived from a study PID.

    The accession must not be the study accession of a stored submission yet.
    """
    logging.basicConfig(level=logging.CRITICAL)
    submission_id = legacy_submission.submit_legacy_metadata_from_path(
        submission_title=submission_title,
        submission_description=submission_description,
        study_accession=study_accession,
        metadata_path=metadata_path,
        config_path=config_path,
    )
    # only reached once the submission is written and its source event published
    typer.echo(f"Submission {submission_id} submitted.")


@cli.command(no_args_is_help=True)
def reserve_study_pid(
    submission_title: str = typer.Option(
        ..., help="The internal name of the study, until its metadata arrives."
    ),
    submission_description: str | None = typer.Option(
        None, help="An optional description of the reservation."
    ),
    config_path: Path = typer.Option(
        ...,
        help="Path to a config YAML.",
        exists=True,
        file_okay=True,
        dir_okay=True,
        readable=True,
    ),
):
    """Reserve a study PID for a study whose metadata has not arrived yet.

    The PID is kept in a new pending submission without content. Hand the PID to the
    submitter, and keep the submission ID: 'submit-pending' needs both once the
    metadata arrives.
    """
    logging.basicConfig(level=logging.CRITICAL)
    submission_id, study_pid = study_pid_reservation.reserve_study_pid_from_path(
        submission_title=submission_title,
        submission_description=submission_description,
        config_path=config_path,
    )
    typer.echo(f"Study PID {study_pid} reserved in submission {submission_id}.")


@cli.command(no_args_is_help=True)
def submit_pending(  # noqa: PLR0913
    submission_id: str = typer.Option(
        ..., help="The ID of the pending submission, as 'reserve-study-pid' printed it."
    ),
    study_pid: str = typer.Option(
        ..., help="The study PID the pending submission holds."
    ),
    submission_title: str = typer.Option(..., help="The title of the submission."),
    submission_description: str = typer.Option(
        ..., help="The description of the submission."
    ),
    metadata_path: Path = typer.Option(
        ...,
        help="The path to the metadata JSON file.",
        exists=True,
        dir_okay=False,
        file_okay=True,
        readable=True,
    ),
    config_path: Path = typer.Option(
        ...,
        help="Path to a config YAML.",
        exists=True,
        file_okay=True,
        dir_okay=True,
        readable=True,
    ),
):
    """Submit metadata to a pending submission, such as a reserved study PID, and
    complete it.

    The study keeps the PID the submission holds, and the datasets get PIDs derived
    from it. Both the submission ID and the study PID are asked for, so that a
    mixed-up ID is refused. A submission that is not pending is refused too.
    """
    logging.basicConfig(level=logging.CRITICAL)
    reserved_title = study_pid_reservation.submit_pending_metadata_from_path(
        submission_id=submission_id,
        study_pid=study_pid,
        submission_title=submission_title,
        submission_description=submission_description,
        metadata_path=metadata_path,
        config_path=config_path,
    )
    # only reached once the submission is completed and its source event published
    typer.echo(f"Submission {submission_id} ('{reserved_title}') submitted.")


def _report_and_confirm_amendment(
    changes: AccessionChanges, *, submission_id: str
) -> bool:
    """Show what an amendment would do and, when it is risky, ask whether to apply it.

    There is deliberately no way to skip the question: an amendment that drops
    accessions removes resources from the running system on the next load, so it
    should only ever be applied by someone who has read the report.

    `typer.confirm` reads the answer with `input()` and does not care whether anything
    is attached to stdin, so a piped `y` would answer for a person who never saw the
    report. A risky amendment is therefore refused outright without a terminal.
    """
    typer.echo(
        amendment.format_amendment_report(submission_id=submission_id, changes=changes)
    )

    if not amendment.needs_confirmation(changes=changes):
        return True

    if not sys.stdin.isatty():
        typer.echo(
            "This amendment needs confirmation, but stdin is not a terminal."
            " Re-run it interactively so the report can be read before answering."
        )
        return False

    return typer.confirm("Apply this amendment?", default=False)


@cli.command(no_args_is_help=True)
def amend(
    submission_id: str = typer.Option(
        ...,
        help="The ID of the submission to amend.",
    ),
    metadata_path: Path = typer.Option(
        ...,
        help="The path to the amended version of the metadata JSON file.",
        exists=True,
        dir_okay=False,
        file_okay=True,
        readable=True,
    ),
    config_path: Path = typer.Option(
        ...,
        help="Path to a config YAML.",
        exists=True,
        file_okay=True,
        dir_okay=True,
        readable=True,
    ),
):
    """Replace the content of a submission with flat accessions, keeping its accessions.

    Use this instead of a second 'submit' when a submission accessioned before study
    PIDs gains files: aliases that are already accessioned keep their accession, and
    only new aliases get new flat ones. A submission with study PIDs is refused.

    The report and the confirmation cover the files only. The other classes keep,
    gain or lose accessions by the same alias matching without a report entry or a
    prompt, and a field changed on an already-accessioned resource is written through.
    Keeping an amendment to added files is a rule for its users, not one this command
    enforces.
    """
    logging.basicConfig(level=logging.CRITICAL)

    def confirm(changes: AccessionChanges) -> bool:
        return _report_and_confirm_amendment(changes, submission_id=submission_id)

    try:
        amendment.amend_metadata_from_path(
            submission_id=submission_id,
            metadata_path=metadata_path,
            config_path=config_path,
            confirm=confirm,
        )
    except AmendmentAbortedError as error:
        typer.echo(str(error))
        raise typer.Abort() from error
    else:
        # only reached once the submission is written and its source event published
        typer.echo(f"Submission {submission_id} amended.")


@cli.command(no_args_is_help=True)
def generate_artifact_models(
    config_path: Path = typer.Option(
        ...,
        help="Path to a config YAML.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
):
    """Run transformation workflow to generate artifact models."""
    logging.basicConfig(level=logging.CRITICAL)
    metadata.generate_artifact_models_from_path(config_path=config_path)


@cli.command(no_args_is_help=True)
def transform(
    config_path: Path = typer.Option(
        ...,
        help="Path to a config YAML.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
):
    """Run transformation workflow on submitted metadata to produce artifacts."""
    logging.basicConfig(level=logging.CRITICAL)
    metadata.transform_metadata_from_path(config_path=config_path)


@cli.command(no_args_is_help=True)
def migrate_accession_store(
    config_path: Path = typer.Option(
        ...,
        help="Path to a config YAML.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
):
    """Convert an accession store that is a flat list of accessions into the JSON
    format of study PIDs, once per store. The original is kept as '<store>.bak'.
    """
    metadata.migrate_accession_store_from_path(config_path=config_path)
