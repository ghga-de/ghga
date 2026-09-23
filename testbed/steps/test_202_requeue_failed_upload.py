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

"""Step definitions for requeueing a file upload that failed interrogation"""

import subprocess
import time
from pathlib import Path
from typing import Any

from fixtures.file import FileBatch

from .conftest import (
    JointFixture,
    Response,
    given,
    parse,
    scenarios,
    then,
    when,
    write_upload_tsv,
)

scenarios("../features/202_requeue_failed_upload.feature")

# No file content can produce this checksum, so the interrogation of the file we
# sabotage always ends in a mismatch and DHFS reports the file as failed.
BOGUS_CHECKSUM = "0" * 64

# Where the file under test is remembered across the scenarios of this feature.
TARGET_STATE = "requeue_target"


def _steward_headers(fixtures: JointFixture) -> dict[str, str]:
    """Return the request headers of the logged-in Data Steward."""
    session = fixtures.auth.get_saved_session(
        name="Data Steward", state_store=fixtures.state
    )
    assert session, "No Data Steward session found"
    return fixtures.auth.headers(session=session)


def _target(fixtures: JointFixture) -> dict[str, Any]:
    """Return what we know about the file under test."""
    target = fixtures.state.get_state(TARGET_STATE)
    assert target, "No file was picked for the requeue scenarios"
    return target


def _remember(fixtures: JointFixture, **fields: Any) -> dict[str, Any]:
    """Add what we have just learned about the file under test to the state."""
    target = fixtures.state.get_state(TARGET_STATE) or {}
    target.update(fields)
    fixtures.state.set_state(TARGET_STATE, target)
    return target


def _read_stable_box(fixtures: JointFixture, storage_name: str) -> dict[str, Any]:
    """Read the upload box back from RS once its version has stopped advancing.

    RS learns about uploads and deletions from events, so a version read right after
    a change is often already out of date, which gets the next update rejected.
    """
    rdub = fixtures.state.get_state(f"rdub_{storage_name}")
    assert rdub, f"No upload box in state for {storage_name} storage"
    url = f"{fixtures.config.rs_url}/upload-boxes/{rdub['id']}"
    headers = _steward_headers(fixtures)

    box: dict[str, Any] = {}
    version = None
    for _ in range(30):
        box = fixtures.http.get(url, headers=headers).json()
        if box.get("version") == version:
            break
        version = box.get("version")
        time.sleep(1)
    assert version is not None, f"Could not read the {storage_name} upload box"

    fixtures.state.set_state(f"rdub_{storage_name}", box)
    return box


def _set_box_state(
    fixtures: JointFixture, storage_name: str, state: str
) -> Response | None:
    """Move the upload box to the given state, or do nothing if it is there already."""
    box = _read_stable_box(fixtures, storage_name)
    if box["state"] == state:
        return None
    url = f"{fixtures.config.rs_url}/upload-boxes/{box['id']}"
    data = {"version": box["version"], "state": state}
    return fixtures.http.patch(url, headers=_steward_headers(fixtures), json=data)


def _list_uploads(fixtures: JointFixture, storage_name: str) -> list[dict[str, Any]]:
    """Return every file upload RS lists for the box of the given storage."""
    rdub = fixtures.state.get_state(f"rdub_{storage_name}")
    assert rdub, f"No upload box in state for {storage_name} storage"
    url = f"{fixtures.config.rs_url}/upload-boxes/{rdub['id']}/uploads"
    response = fixtures.http.get(
        url, headers=_steward_headers(fixtures), params={"limit": 1000}
    )
    assert response.status_code == 200, f"{response.status_code}: {response.text}"
    return response.json()["items"]


def _find_upload(
    fixtures: JointFixture, storage_name: str, alias: str
) -> dict[str, Any] | None:
    """Return the file upload RS lists under the given alias, if there is one."""
    uploads = [
        upload
        for upload in _list_uploads(fixtures, storage_name)
        if upload["alias"] == alias
    ]
    # A deleted upload keeps its alias, so the replacement is the one that is not
    # 'cancelled'. RS learns of a deletion from an event, so the old upload can
    # briefly still look live, and the newest record is then the replacement.
    live = [upload for upload in uploads if upload["state"] != "cancelled"]
    live.sort(key=lambda upload: upload["state_updated"], reverse=True)
    return live[0] if live else None


def _wait_for_init_upload(
    fixtures: JointFixture, alias: str, timeout: float = 120
) -> dict[str, Any]:
    """Wait for UCS to have initiated the upload of the given alias and return it.

    This is the window in which the file can be sabotaged: UCS knows the object ID
    and the part layout, but has not told FIS about the file yet.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        documents = fixtures.mongo.find_documents(
            db_name=fixtures.config.ucs_db_name,
            collection_name=fixtures.config.ucs_file_uploads_collection,
            query={"alias": alias, "state": "init"},
        )
        if documents:
            assert len(documents) == 1, (
                f"Expected one initiated upload for alias {alias!r}, got {documents}"
            )
            return documents[0]
        time.sleep(0.1)
    raise AssertionError(
        f"UCS did not initiate an upload for alias {alias!r} within {timeout} seconds"
    )


def _seed_fis_file(fixtures: JointFixture, ucs_document: dict[str, Any]) -> None:
    """Give FIS a copy of the file with a checksum the content cannot produce.

    FIS ignores a file upload until it reaches the inbox, and its insert is a no-op
    once the file is known, so writing the record while the upload is still being
    initiated is what makes DHFS interrogate the file against the wrong checksum.
    Seeding it after the fact would race DHFS, which polls FIS for new files.

    Every other field is UCS's own, so only the checksum is made up. Requeueing the
    file lets FIS rewrite the record from the FileUpload event, which restores the
    real checksum and lets the second interrogation pass.
    """
    document = {
        "_id": ucs_document["_id"],
        "storage_alias": ucs_document["storage_alias"],
        "bucket_id": ucs_document["bucket_id"],
        "object_id": {"$uuid": ucs_document["object_id"]},
        "decrypted_sha256": BOGUS_CHECKSUM,
        "decrypted_size": ucs_document["decrypted_size"],
        "encrypted_size": ucs_document["encrypted_size"],
        "part_size": ucs_document["part_size"],
        "state": "inbox",
        # Written as the string SMS handed us rather than a date: FIS rewrites the
        # record when it stores the failure report, and nothing compares timestamps
        # before then.
        "state_updated": ucs_document["state_updated"],
        "interrogated": False,
        "can_remove": False,
    }
    fixtures.mongo.upsert_document(
        db_name=fixtures.config.fis_db_name,
        collection_name=fixtures.config.fis_files_collection,
        document=document,
    )


@given(parse('the data upload box for "{storage_name}" storage is unlocked'))
def unlock_upload_box(storage_name: str, fixtures: JointFixture):
    """Move the upload box back to 'open' so a file can be replaced."""
    response = _set_box_state(fixtures, storage_name, "open")
    if response is not None:
        assert response.status_code == 204, f"{response.status_code}: {response.text}"


@when(
    parse(
        'the largest file of dataset "{dataset_alias}" is deleted from "{storage_name}" storage'
    )
)
def delete_largest_file(
    dataset_alias: str,
    storage_name: str,
    fixtures: JointFixture,
    file_fixture: dict[str, FileBatch],
):
    """Delete the biggest file of the dataset so it can be uploaded again.

    The biggest file takes the longest to upload, which leaves the widest window
    for seeding FIS while the upload is still being initiated.
    """
    alias, file_path = max(
        file_fixture[dataset_alias].file_info, key=lambda info: info[1].stat().st_size
    )
    upload = _find_upload(fixtures, storage_name, alias)
    assert upload, f"No file upload listed for alias {alias!r}"

    rdub = fixtures.state.get_state(f"rdub_{storage_name}")
    url = f"{fixtures.config.rs_url}/upload-boxes/{rdub['id']}/uploads/{upload['id']}"
    response = fixtures.http.delete(url, headers=_steward_headers(fixtures))
    assert response.status_code == 204, f"{response.status_code}: {response.text}"

    fixtures.state.set_state(
        TARGET_STATE,
        {
            "alias": alias,
            "file_path": str(file_path),
            "storage_name": storage_name,
            "deleted_id": upload["id"],
        },
    )


@when(
    parse(
        'that file is uploaded to "{storage_name}" storage with a corrupted expected checksum'
    )
)
def upload_file_with_corrupted_checksum(storage_name: str, fixtures: JointFixture):
    """Upload the file again and make FIS expect a checksum it cannot match."""
    target = _target(fixtures)
    alias = target["alias"]
    connector = fixtures.connector
    connector.config.file_metadata_dir.mkdir(exist_ok=True)
    upload_token = fixtures.state.get_state(f"upload token for {storage_name}")
    assert upload_token, f"No upload token found for {storage_name}"

    tsv_path = write_upload_tsv(
        [(alias, Path(target["file_path"]))], connector.config.work_dir
    )
    cmd = ["ghga-connector", "batch-upload", "--tsv", str(tsv_path), "--overwrite"]
    # The connector writes to a file rather than a pipe: we let it run while seeding
    # FIS, and a pipe would deadlock the upload once its buffer filled up.
    log_path = connector.config.work_dir / "corrupted_upload.log"
    with log_path.open("w", encoding="utf-8") as log_file:
        process = subprocess.Popen(  # nosec B607, B603
            cmd,
            cwd=connector.config.work_dir,
            stdin=subprocess.PIPE,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            assert process.stdin is not None
            process.stdin.write(f"{upload_token}\n")
            process.stdin.flush()
            process.stdin.close()

            ucs_document = _wait_for_init_upload(fixtures, alias)
            assert ucs_document["_id"] != target["deleted_id"], (
                "UCS still reports the deleted upload as being initiated"
            )
            _seed_fis_file(fixtures, ucs_document)

            process.wait(timeout=300)
        except BaseException:
            process.kill()
            process.wait()
            raise

    output = log_path.read_text(encoding="utf-8")
    print(output)
    assert "Successfully uploaded" in output, f"The connector failed:\n{output}"


@then(parse('the file is listed as "{expected_state}" within "{seconds:d}" seconds'))
def check_file_state(expected_state: str, seconds: int, fixtures: JointFixture):
    """Wait for RS to list the file under test in the expected state."""
    target = _target(fixtures)
    alias = target["alias"]
    deadline = time.monotonic() + seconds
    upload = None
    while time.monotonic() < deadline:
        upload = _find_upload(fixtures, target["storage_name"], alias)
        if upload and upload["state"] == expected_state:
            fields = {"file_id": upload["id"]}
            # The inbox object ID has to be kept: once the file is interrogated,
            # the record points at the object in the interrogation bucket instead.
            if expected_state == "failed_interrogation":
                fields["inbox_object_id"] = upload["object_id"]
            _remember(fixtures, **fields)
            return
        time.sleep(2)
    raise AssertionError(
        f"File {alias!r} is not {expected_state!r} after {seconds} seconds: {upload}"
    )


@then("the file reports why it failed")
def check_failure_reason(fixtures: JointFixture):
    """Assert the file carries the reason the interrogation gave."""
    target = _target(fixtures)
    upload = _find_upload(fixtures, target["storage_name"], target["alias"])
    assert upload and upload.get("failure_reason"), (
        f"No failure reason on the failed file: {upload}"
    )


@then("the file no longer reports why it failed")
def check_failure_reason_cleared(fixtures: JointFixture):
    """Assert the requeue cleared the failure reason, which archival insists on."""
    target = _target(fixtures)
    upload = _find_upload(fixtures, target["storage_name"], target["alias"])
    assert upload and not upload.get("failure_reason"), (
        f"The failure reason survived the requeue: {upload}"
    )


@then("the interrogation report for the file has been discarded")
def check_report_discarded(fixtures: JointFixture):
    """Assert FIS dropped the report of the interrogation that failed."""
    file_id = _target(fixtures)["file_id"]
    removed = fixtures.mongo.wait_for_removal(
        db_name=fixtures.config.fis_db_name,
        collection_name=fixtures.config.fis_reports_collection,
        query={"_id": file_id},
        timeout=30,
        interval=0.5,
    )
    assert removed, f"FIS still holds an interrogation report for file {file_id}"


@then(
    parse(
        'the uploaded object is still in the "{bucket}" bucket of "{storage_name}" storage'
    )
)
def check_object_kept(bucket: str, storage_name: str, fixtures: JointFixture):
    """Assert the failed file's object was kept, so no second upload is needed."""
    storage_config = fixtures.s3.get_storage_config(storage_name)
    object_id = _target(fixtures)["inbox_object_id"]
    assert fixtures.s3.does_object_exist(
        storage_alias=storage_config.storage_alias,
        bucket=getattr(storage_config.buckets, bucket),
        object_id=object_id,
    ), f"{object_id} is gone from the {bucket} bucket of {storage_name} storage"


@then(
    parse(
        'the uploaded object is gone from the "{bucket}" bucket of "{storage_name}" storage'
    )
)
def check_object_removed(bucket: str, storage_name: str, fixtures: JointFixture):
    """Assert the object was cleaned up once the interrogation passed."""
    storage_config = fixtures.s3.get_storage_config(storage_name)
    object_id = _target(fixtures)["inbox_object_id"]
    assert not fixtures.s3.does_object_exist(
        storage_alias=storage_config.storage_alias,
        bucket=getattr(storage_config.buckets, bucket),
        object_id=object_id,
    ), f"{object_id} is still in the {bucket} bucket of {storage_name} storage"


@when(
    parse('"{full_name}" requeues the failed file in "{storage_name}" storage'),
    target_fixture="response",
)
def requeue_failed_file(
    full_name: str, storage_name: str, fixtures: JointFixture
) -> Response:
    """Requeue the failed file through RS, as a Data Steward would."""
    rdub = fixtures.state.get_state(f"rdub_{storage_name}")
    file_id = _target(fixtures)["file_id"]
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    assert session, f"No session found for {full_name}"

    url = (
        f"{fixtures.config.rs_url}/upload-boxes/{rdub['id']}/uploads/{file_id}/requeue"
    )
    return fixtures.http.post(url, headers=fixtures.auth.headers(session=session))


@when(
    parse('"{full_name}" locks the data upload box for "{storage_name}" storage again'),
    target_fixture="response",
)
def lock_upload_box_again(
    full_name: str, storage_name: str, fixtures: JointFixture
) -> Response:
    """Lock the upload box again, leaving the journey where this feature found it."""
    response = _set_box_state(fixtures, storage_name, "locked")
    assert response is not None, f"The {storage_name} upload box was already locked"
    return response
