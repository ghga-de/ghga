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

"""Step definitions for uploading files"""

import signal
import subprocess
import time
from pathlib import Path

from fixtures.auth import Session
from fixtures.file import FileBatch

from .conftest import (
    Config,
    JointFixture,
    MongoFixture,
    Response,
    StateStorage,
    given,
    parse,
    run_batch_upload,
    scenarios,
    then,
    when,
    write_upload_tsv,
)

scenarios("../features/201_user_file_upload.feature")


@when(
    parse('"{full_name}" creates an upload work package for "{storage_name}" storage'),
    target_fixture="response",
)
def create_work_package(full_name: str, fixtures: JointFixture, storage_name: str):
    """Create an upload work package for the specified storage scope."""
    rdub = fixtures.state.get_state(f"rdub_{storage_name}")
    rdub_state = rdub.get("state")
    assert rdub_state == "open", (
        f"Expected active upload box for {storage_name}, got {rdub_state}"
    )
    data = {
        "type": "upload",
        "research_data_upload_box_id": rdub["id"],
        "user_public_crypt4gh_key": fixtures.config.user_public_crypt4gh_key,
    }
    url = f"{fixtures.config.wps_url}/work-packages"

    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    headers = fixtures.auth.headers(session=session)
    return fixtures.http.post(url, headers=headers, json=data)


@then(parse('the response contains an upload token for "{storage_name}" storage'))
def check_upload_token(fixtures: JointFixture, response: Response, storage_name: str):
    """Check that the response contains an upload token and save it in the state."""
    data = response.json()
    assert set(data) == {"id", "token", "expires"}
    id_, token = data["id"], data["token"]
    assert 20 <= len(id_) < 40 and 80 < len(token) < 120
    id_and_token = f"{id_}:{token}"
    fixtures.state.set_state(f"upload token for {storage_name}", id_and_token)


@given("no upload work packages have been created yet")
def remove_wps_upload_data(config: Config, mongo: MongoFixture, state: StateStorage):
    """Remove all upload work packages from the database and unset the state."""
    mongo.remove_documents(
        db_name=config.wps_db_name,
        collection_name="workPackages",
        query={"type": "upload"},
    )
    state.unset_state("upload token for")


@given("the upload buckets are empty")
def upload_buckets_empty(fixtures: JointFixture):
    for storage_name in ["primary", "secondary"]:
        storage_config = fixtures.s3.get_storage_config(storage_name)
        fixtures.s3.empty_buckets(
            storages=storage_config,
            buckets=[storage_config.buckets.inbox],
        )


@then(
    parse(
        'the uploaded files exist in the "{bucket}" bucket of "{storage_name}" storage'
    )
)
def check_uploaded_files_in_storage(
    fixtures: JointFixture, response: Response, storage_name: str, bucket: str
):
    """Check that the uploaded files exist in the given bucket.

    The box version used for locking is read live from the server at lock time
    (see lock_upload_box), not derived from the file count here, because the count
    can diverge from the version once uploads are added and removed.
    """
    storage_config = fixtures.s3.get_storage_config(storage_name)
    bucket_id = getattr(storage_config.buckets, bucket)
    uploaded_files = response.json()
    for file_upload in uploaded_files:
        assert "object_id" in file_upload
        object_id = str(file_upload["object_id"])
        assert fixtures.s3.does_object_exist(
            storage_alias=storage_config.storage_alias,
            bucket=bucket_id,
            object_id=object_id,
        ), f"{object_id} does not exist in the staging bucket"


@when(
    parse('"{full_name}" locks the data upload box for "{storage_name}" storage'),
    target_fixture="response",
)
def lock_upload_box(full_name: str, storage_name: str, fixtures: JointFixture):
    """Lock the data upload box for the specified storage scope."""
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

    # The box version is a counter that advances oncevery upload and delete,
    # it can diverge from the uploaded-file count (see the interrupted-upload scenario).
    # Read the live version from the server instead of assuming version
    box = fixtures.http.get(url, headers=headers).json()
    version = box["version"]
    rdub["version"] = version
    fixtures.state.set_state(f"rdub_{storage_name}", rdub)

    data = {"version": version, "state": "locked"}
    return fixtures.http.patch(url, headers=headers, json=data)


@when(
    parse(
        'uploading a file from "{dataset_alias}" to "{storage_name}" storage is interrupted'
    )
)
def start_and_interrupt_upload(
    dataset_alias: str,
    storage_name: str,
    fixtures: JointFixture,
    file_fixture: dict[str, FileBatch],
):
    """Start uploading a file, then interrupt the connector mid-flight.

    The interrupted file is recorded in the "last_uploaded_files" state so
    later steps can re-upload it, assert on it, and finally delete it, all without
    naming it in the Gherkin.
    """
    # Any file works as long as the choice is consistent across runs.
    object_id, file_path = max(file_fixture[dataset_alias].file_info)
    fixtures.connector.config.file_metadata_dir.mkdir(exist_ok=True)
    upload_token = fixtures.state.get_state(f"upload token for {storage_name}")
    assert upload_token is not None, f"No upload token found for {storage_name}"

    tsv_path = write_upload_tsv(
        [(object_id, file_path)], fixtures.connector.config.work_dir
    )
    cmd = ["ghga-connector", "batch-upload", "--tsv", str(tsv_path)]
    # Capture the connector output so we can watch for the upload to start.
    process = subprocess.Popen(  # nosec B607, B603
        cmd,
        cwd=fixtures.connector.config.work_dir,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        assert process.stdin is not None
        process.stdin.write(f"{upload_token}\n")
        process.stdin.flush()
        # Read output until the upload starts, then interrupt it, leaving a
        # cancellable, incomplete upload in the box.
        assert process.stdout is not None
        for line in process.stdout:
            if "uploading file" in line.lower():
                break
    finally:
        # Interrupt with SIGINT so the connector can abort the in-flight upload.
        process.send_signal(signal.SIGINT)
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    # Start a fresh worklist of files to be deleted at the end of the scenario.
    fixtures.state.set_state(
        "last_uploaded_files",
        [{"object_id": object_id, "file_path": str(file_path)}],
    )


@then(parse('the uploaded files are listed as "{expected_state}"'))
@then(parse('the uploaded file is listed as "{expected_state}"'))
def check_uploaded_file_state(
    expected_state: str, fixtures: JointFixture, response: Response
):
    """Assert the most recently uploaded file is listed in the given state.

    The file is matched by comparing our stored object_id to the alias of the
    returned upload records.
    """
    uploaded = fixtures.state.get_state("last_uploaded_files") or []
    assert uploaded, "No uploaded file was recorded"
    object_id = uploaded[-1]["object_id"]
    uploads = response.json()
    matching = [upload for upload in uploads if str(upload.get("alias")) == object_id]
    assert matching, f"Uploaded file {object_id!r} not found in uploads: {uploads}"
    states = {upload.get("state") for upload in matching}
    assert expected_state in states, (
        f"Expected uploaded file state {expected_state!r}, got {states}"
    )
    # Capture the database id of the listed file so deletion can target it by id.
    selected = next(
        upload for upload in matching if upload.get("state") == expected_state
    )
    uploaded[-1]["id"] = selected["id"]
    fixtures.state.set_state("last_uploaded_files", uploaded)


@when(parse('the interrupted file is re-uploaded to "{storage_name}" storage'))
def reupload_interrupted_file(storage_name: str, fixtures: JointFixture):
    """Re-upload the previously interrupted file; must succeed without error."""
    uploaded = fixtures.state.get_state("last_uploaded_files") or []
    assert uploaded, "No uploaded file was recorded"
    interrupted = uploaded[-1]
    fixtures.connector.config.file_metadata_dir.mkdir(exist_ok=True)
    upload_token = fixtures.state.get_state(f"upload token for {storage_name}")
    assert upload_token is not None, f"No upload token found for {storage_name}"
    completed_upload = run_batch_upload(
        file_info=[(interrupted["object_id"], Path(interrupted["file_path"]))],
        fixtures=fixtures,
        upload_token=upload_token,
    )
    assert "Successfully uploaded" in completed_upload.stdout


@when(
    parse('another file from "{dataset_alias}" is uploaded to "{storage_name}" storage')
)
def upload_another_file(
    dataset_alias: str,
    storage_name: str,
    fixtures: JointFixture,
    file_fixture: dict[str, FileBatch],
):
    """Upload an additional file and wait for it to complete."""
    # Any file other than the interrupted one works as long as it is consistent.
    object_id, file_path = min(file_fixture[dataset_alias].file_info)
    fixtures.connector.config.file_metadata_dir.mkdir(exist_ok=True)
    upload_token = fixtures.state.get_state(f"upload token for {storage_name}")
    assert upload_token is not None, f"No upload token found for {storage_name}"
    completed_upload = run_batch_upload(
        file_info=[(object_id, file_path)],
        fixtures=fixtures,
        upload_token=upload_token,
    )
    assert "Successfully uploaded" in completed_upload.stdout
    uploaded = fixtures.state.get_state("last_uploaded_files") or []
    uploaded.append({"object_id": object_id, "file_path": str(file_path)})
    fixtures.state.set_state("last_uploaded_files", uploaded)


@then(parse('the uploaded files are listed as "{first_state}" or "{second_state}"'))
def check_uploaded_files_states(
    first_state: str,
    second_state: str,
    fixtures: JointFixture,
    response: Response,
):
    """Assert every uploaded file is listed in one of the two allowed states.

    Each uploaded file is matched by comparing our stored object_id to the alias
    of the returned upload records.
    """
    uploaded = fixtures.state.get_state("last_uploaded_files") or []
    assert len(uploaded) >= 2, "Expected at least the two uploaded files in state"
    allowed = {first_state, second_state}
    alias_to_record = {str(upload.get("alias")): upload for upload in response.json()}
    for file in uploaded:
        object_id = file["object_id"]
        record = alias_to_record.get(object_id)
        assert record, (
            f"Uploaded file {object_id!r} not listed: {list(alias_to_record)}"
        )
        state = record.get("state")
        assert state in allowed, (
            f"Uploaded file {object_id!r} expected state in {allowed}, got {state!r}"
        )
        # Capture the database id of each listed file so deletion can target it by id.
        file["id"] = record["id"]
    fixtures.state.set_state("last_uploaded_files", uploaded)


@when(
    parse('the uploaded files are deleted from "{storage_name}" storage'),
    target_fixture="response",
)
def delete_uploaded_files(storage_name: str, fixtures: JointFixture) -> Response | None:
    """Delete the files uploaded during this scenario.

    Files are deleted by their database id, which the "listed as" steps captured into
    "last_uploaded_files" (our object_id is only the alias). This restores the box to
    its pre-scenario baseline so the rest of the journey is unaffected.
    """
    assert storage_name in ["primary", "secondary"], f"Unknown storage: {storage_name}"
    uploaded = fixtures.state.get_state("last_uploaded_files") or []

    rdub = fixtures.state.get_state(f"rdub_{storage_name}")
    rdub_id = rdub["id"]

    sub = fixtures.state.get_state("logged in as")
    assert sub
    current_session = fixtures.auth.get_saved_session(
        name=sub, state_store=fixtures.state
    )
    assert current_session, f"No saved session for {sub}"

    headers = fixtures.auth.headers(session=current_session)

    uploads_url = f"{fixtures.config.rs_url}/upload-boxes/{rdub_id}/uploads"
    response: Response | None = None
    for file in uploaded:
        file_id = file.get("id")
        assert file_id, (
            f"No database id stored for uploaded file {file['object_id']!r}; "
            "the 'is listed as' steps must run first to capture it"
        )
        delete_url = f"{uploads_url}/{file_id}"
        response = fixtures.http.delete(delete_url, headers=headers)
        assert response.status_code == 204, f"{response.status_code}: {response.text}"

    return response
