# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
#

"""Shared test used for steps with prefix test_3*"""

import subprocess
from pathlib import Path
from uuid import UUID

from fixtures import Config, JointFixture, Response, StateStorage  # noqa: RUF100
from fixtures.file import FileBatch, subset_file_batch_by_scope
from pytest_bdd import (  # noqa: RUF100
    given,
    then,
    when,
)

from steps.utils import parse


@when(
    parse('"{full_name}" retrieves the list of data upload boxes'),
    target_fixture="response",
)
def retrieve_list_of_rdubs(full_name: str, fixtures: JointFixture) -> Response:
    """Retrieve the list of research data upload boxes."""
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    assert session, f"No session found for {full_name}"
    assert session.user_id, f"user_id is missing for {full_name}"

    url = f"{fixtures.config.rs_url}/upload-boxes"
    headers = fixtures.auth.headers(session=session)
    return fixtures.http.get(url, headers=headers)


@when(
    parse(
        '"{full_name}" retrieves the research data upload boxes for "{storage_name}" storage'
    ),
    target_fixture="response",
)
def retrieve_rdub(
    full_name: str, storage_name: str, fixtures: JointFixture
) -> Response:
    """Create a data upload box for the specified storage scope."""
    assert storage_name in ["primary", "secondary"], f"Unknown storage: {storage_name}"
    rdub = fixtures.state.get_state(f"rdub_{storage_name}")
    rdub_id = rdub["id"]
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    assert session, f"No session found for {full_name}"
    assert session.user_id, f"user_id is missing for {full_name}"

    url = f"{fixtures.config.rs_url}/upload-boxes/{rdub_id}"
    headers = fixtures.auth.headers(session=session)
    return fixtures.http.get(url, headers=headers)


@when(
    parse(
        '"{full_name}" retrieves the list of files uploaded to the box for "{storage_name}" storage'
    ),
    target_fixture="response",
)
def retrieves_files_uploaded_to_box(
    full_name: str, storage_name: str, fixtures: JointFixture
) -> Response:
    """Create a data upload box for the specified storage scope."""
    assert storage_name in ["primary", "secondary"], f"Unknown storage: {storage_name}"
    rdub = fixtures.state.get_state(f"rdub_{storage_name}")
    rdub_id = rdub["id"]
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    assert session, f"No session found for {full_name}"
    assert session.user_id, f"user_id is missing for {full_name}"

    url = f"{fixtures.config.rs_url}/upload-boxes/{rdub_id}/uploads"
    headers = fixtures.auth.headers(session=session)
    return fixtures.http.get(url, headers=headers)


@then(parse('the research data upload box state is "{expected_state}"'))
def check_rdub_state(state: StateStorage, expected_state: str, response: Response):
    """Check that the research data upload box has the expected state."""
    data = response.json()
    actual_state = data.get("state")
    assert actual_state == expected_state, (
        f"Expected upload box state '{expected_state}', got '{actual_state}'"
    )
    storage_alias = data.get("storage_alias")
    state.set_state(f"rdub_{storage_alias}", data)


@then(parse('all files uploaded to "{storage_name}" are "{expected_state}"'))
def check_all_files_state(
    storage_name: str, expected_state: str, fixtures: JointFixture, response: Response
):
    """Check that every uploaded file for the given storage is in the expected state."""
    files = response.json()
    if isinstance(files, dict):  # paginated: {"items": [...], "total_count": n}
        files = files.get("items", files)
    assert isinstance(files, list), f"Expected a list of files, got {type(files)}"

    storage_config = fixtures.s3.get_storage_config(storage_name)

    if expected_state == "interrogated":
        bucket_id = storage_config.buckets.staging
        for file in files:
            # FIXME This is not ideal, they can be queried all at once,
            # but SMS does not support in query in id fields
            file_id = file.get("id")
            query = {
                "storage_alias": storage_config.storage_alias,
                "bucket_id": bucket_id,
                "_id": file_id,
            }
            fis_document = fixtures.mongo.wait_for_document(
                db_name=fixtures.config.fis_db_name,
                collection_name=fixtures.config.fis_reports_collection,
                query=query,
                timeout=60,
                interval=0.5,
            )
            ucs_document = fixtures.mongo.wait_for_document(
                db_name=fixtures.config.ucs_db_name,
                collection_name=fixtures.config.ucs_file_uploads_collection,
                query=query,
                timeout=60,
                interval=0.5,
            )
            for document, collection in ((fis_document, "FIS"), (ucs_document, "UCS")):
                assert document is not None, (
                    f"Timed out waiting for {collection} file {file_id!r} to be '{expected_state}' in {storage_name} storage"
                )

    if expected_state == "archived":
        for file in files:
            # FIXME This is not ideal, they can be queried all at once,
            # but SMS API does not support "in" query with id fields
            file_id = file.get("id")
            query = {
                "storage_alias": storage_config.storage_alias,
                "bucket_id": storage_config.buckets.permanent,
                "_id": file_id,
            }
            ifrs_document = fixtures.mongo.wait_for_document(
                db_name=fixtures.config.ifrs_db_name,
                collection_name=fixtures.config.ifrs_metadata_collection,
                query=query,
                timeout=60,
                interval=0.5,
            )
            assert ifrs_document is not None, (
                f"Timed out waiting for IFRS file {file_id!r} to be '{expected_state}' in {storage_name} storage"
            )

    fixtures.state.set_state(f"rdub_{storage_name}_files", files)


# Shared file-upload step (CLI) reused by the API (201) and UI (501-2)


def write_upload_tsv(file_info: list[tuple[str, Path]], dest_dir: Path) -> Path:
    """Write a batch-upload manifest and return its path.

    `ghga-connector batch-upload --tsv` expects a tab-separated file whose first
    column is the file path and second column the file alias, no headers.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    tsv_path = dest_dir / "batch_upload.tsv"
    lines = [f"{file_path}\t{object_id}" for object_id, file_path in file_info]
    tsv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return tsv_path


def run_batch_upload(
    file_info: list[tuple[str, Path]], fixtures: JointFixture, upload_token: str
) -> subprocess.CompletedProcess:
    """Run ghga-connector batch-upload and return the completed process.

    Only the invariants shared by every run are asserted here; the caller decides
    what the outcome should look like.
    """
    connector = fixtures.connector
    tsv_path = write_upload_tsv(file_info, connector.config.work_dir)
    cmd = ["ghga-connector", "batch-upload", "--tsv", str(tsv_path), "--debug"]
    completed_upload = subprocess.run(  # nosec B607, B603
        cmd,
        cwd=connector.config.work_dir,
        input=upload_token,
        capture_output=True,
        check=False,
        encoding="utf-8",
        text=True,
        timeout=180,
    )

    print("Output:")
    print(completed_upload.stdout)
    if completed_upload.stderr:
        print("Error:")
        print(completed_upload.stderr)

    assert "Please paste the complete access token" in completed_upload.stdout
    assert "ERROR" not in completed_upload.stderr
    return completed_upload


def _resolve_upload_batch(
    fixtures: JointFixture,
    file_fixture: dict[str, FileBatch],
    file_scope: str,
    dataset_alias: str,
    storage_name: str,
) -> tuple[list[tuple[str, Path]], str]:
    """Resolve the (file_info, upload_token) for a dataset's files (optional scope)."""
    file_metadata_dir = fixtures.connector.config.file_metadata_dir
    file_metadata_dir.mkdir(exist_ok=True)

    assert file_fixture.keys() == {"DS_A", "DS_B"}
    assert dataset_alias in file_fixture, f"Dataset {dataset_alias} not found"
    upload_token = fixtures.state.get_state(f"upload token for {storage_name}")
    assert upload_token is not None, f"No upload token found for {storage_name}"

    file_batch = file_fixture[dataset_alias]
    if file_scope != "all":
        file_batch = subset_file_batch_by_scope(file_fixture[dataset_alias], file_scope)
    return file_batch.file_info, upload_token


@when(
    parse(
        '"{file_scope}" files of dataset "{dataset_alias}" are uploaded to "{storage_name}" storage'
    )
)
def upload_files_as_batch(
    fixtures: JointFixture,
    file_fixture: dict[str, FileBatch],
    file_scope: str,
    dataset_alias: str,
    storage_name: str,
):
    """Upload a dataset's files (optionally a single file-type scope) via the connector."""
    file_info, upload_token = _resolve_upload_batch(
        fixtures, file_fixture, file_scope, dataset_alias, storage_name
    )
    completed_upload = run_batch_upload(
        file_info=file_info, fixtures=fixtures, upload_token=upload_token
    )
    assert "Successfully uploaded" in completed_upload.stdout


@when(
    parse(
        '"{file_scope}" files of dataset "{dataset_alias}" are uploaded again to "{storage_name}" storage'
    ),
    target_fixture="completed_process",
)
def reupload_files_as_batch(
    fixtures: JointFixture,
    file_fixture: dict[str, FileBatch],
    file_scope: str,
    dataset_alias: str,
    storage_name: str,
) -> subprocess.CompletedProcess:
    """Re-run batch-upload for a dataset's files; already-uploaded files are skipped."""
    file_info, upload_token = _resolve_upload_batch(
        fixtures, file_fixture, file_scope, dataset_alias, storage_name
    )
    return run_batch_upload(file_info, fixtures, upload_token)


@then("the connector reports the files were already uploaded")
def check_files_already_uploaded(completed_process: subprocess.CompletedProcess):
    """Assert the connector skipped an all-duplicate batch upload."""
    assert "All files are already uploaded. Nothing to do." in completed_process.stdout


@then(parse('the response contains an upload box ID for "{storage_name}" storage'))
def check_upload_box(fixtures: JointFixture, response: Response, storage_name: str):
    boxes = response.json().get("boxes")
    assert isinstance(boxes, list), "Response does not contain a list of boxes"
    assert len(boxes) != 0, "Response does not contain any boxes"
    storage_alias = fixtures.s3.get_storage_config(storage_name).storage_alias

    filtered_boxes = [box for box in boxes if box.get("storage_alias") == storage_alias]
    assert len(filtered_boxes) != 0, f"No box found for storage alias '{storage_alias}'"
    rdub = filtered_boxes[0]

    try:
        UUID(rdub.get("id"), version=4)  # assert ID is in uuid 4 format
    except (ValueError, TypeError) as e:
        raise AssertionError(f"ID '{rdub.get('id')}' is not a valid UUID v4 {e}") from e

    fixtures.state.set_state(f"rdub_{storage_name}", rdub)
