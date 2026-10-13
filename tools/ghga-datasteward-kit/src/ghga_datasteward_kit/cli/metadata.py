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
from pathlib import Path

import typer

from ghga_datasteward_kit import amendment, metadata
from ghga_datasteward_kit.amendment import AccessionChanges
from ghga_datasteward_kit.exceptions import AmendmentAbortedError
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


def _report_and_confirm_amendment(
    changes: AccessionChanges, *, submission_id: str
) -> bool:
    """Show what an amendment would do and, when it is risky, ask whether to apply it.

    There is deliberately no way to skip the question: an amendment that drops
    accessions removes resources from the running system on the next load, so it
    should only ever be applied by someone who has read the report.
    """
    typer.echo(
        amendment.format_amendment_report(submission_id=submission_id, changes=changes)
    )

    if not amendment.needs_confirmation(changes=changes):
        return True

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
    """Add to an already accessioned submission, keeping its existing accessions.

    Use this instead of a second 'submit' when a submission gains files: aliases that
    are already accessioned keep their accession, and only new aliases get new ones.
    """
    logging.basicConfig(level=logging.CRITICAL)

    def confirm(changes: AccessionChanges) -> bool:
        return _report_and_confirm_amendment(changes, submission_id=submission_id)

    try:
        diff = amendment.amend_metadata_from_path(
            submission_id=submission_id,
            metadata_path=metadata_path,
            config_path=config_path,
            confirm=confirm,
        )
    except AmendmentAbortedError as error:
        typer.echo(str(error))
        raise typer.Abort() from error

    typer.echo(amendment.format_amendment_result(diff=diff))


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


@cli.command()
def compare_aliases(
    metadata_path: Path = typer.Argument(
        ...,
        help="The path to the metadata JSON file.",
        exists=True,
        dir_okay=False,
        file_okay=True,
        readable=True,
    ),
    tsv: Path = typer.Argument(
        ...,
        help=(
            "Path to a tsv file with the first column containing the file path and the"
            + " second column containing the file alias."
        ),
        exists=True,
        dir_okay=False,
        file_okay=True,
        readable=True,
    ),
):
    """Compare the file aliases contained in the transpiled metadata JSON file with
    those in the file upload TSV file.

    Any aliases from the file upload TSV file which are absent in the metadata
    JSON file will be reported.
    """
    metadata.compare_aliases(metadata_path=metadata_path, file_overview_tsv=tsv)
