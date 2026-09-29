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

"""Step definitions for resolving file uploads that failed interrogation"""

import re
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fixtures.file import FileBatch
from playwright.sync_api import Locator, Page, expect

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
from .utils import UI_TIMEOUT, has_reached

scenarios("../features/202_requeue_failed_upload.feature")

# No file content can produce this checksum, so the interrogation of the files we
# sabotage always ends in a mismatch and DHFS reports them as failed.
BOGUS_CHECKSUM = "0" * 64

# Where the files under test are remembered across the scenarios of this feature.
# The "first" one is resolved by requeueing it alone, the "second" one by deleting
# it and the "third" one by requeueing every failed file of the box.
TARGETS_STATE = "requeue_targets"
ORDINALS = ("first", "second", "third")


def _headers(fixtures: JointFixture, full_name: str = "Data Steward") -> dict[str, str]:
    """Return the request headers of the given logged-in user.

    Every step of this feature acts as a Data Steward, which is the default for the
    reads that no step text names an actor for.
    """
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    assert session, f"No session found for {full_name}"
    return fixtures.auth.headers(session=session)


def _targets(fixtures: JointFixture) -> dict[str, dict[str, Any]]:
    """Return what we know about all files under test."""
    targets = fixtures.state.get_state(TARGETS_STATE)
    assert targets, "No files were picked for the requeue scenarios"
    return targets


def _target(fixtures: JointFixture, ordinal: str) -> dict[str, Any]:
    """Return what we know about one of the files under test."""
    assert ordinal in ORDINALS, f"Unknown file {ordinal!r}"
    return _targets(fixtures)[ordinal]


def _remember(fixtures: JointFixture, ordinal: str, **fields: Any) -> None:
    """Add what we have just learned about one file under test to the state."""
    targets = fixtures.state.get_state(TARGETS_STATE) or {}
    targets.setdefault(ordinal, {}).update(fields)
    fixtures.state.set_state(TARGETS_STATE, targets)


def _file_row(page: Page, alias: str) -> Locator:
    """Return the row of the portal's file list that shows the given file."""
    rows = page.locator("app-upload-box-files-table table tbody tr")
    return rows.filter(has_text=alias)


def _retry_button(page: Page, alias: str) -> Locator:
    """Return the portal's button that requeues the given file."""
    return _file_row(page, alias).get_by_role(
        "button", name=f"Retry re-encryption of {alias}"
    )


def _retry_all_button(page: Page) -> Locator:
    """Return the portal's button that requeues every failed file of the box."""
    return page.get_by_role("button", name="Retry failed re-encryptions")


def _read_stable_box(
    fixtures: JointFixture, storage_name: str, full_name: str = "Data Steward"
) -> dict[str, Any]:
    """Read the upload box back from RS once its version has stopped advancing.

    RS learns about uploads and deletions from events, so a version read right after
    a change is often already out of date, which gets the next update rejected.
    """
    rdub = fixtures.state.get_state(f"rdub_{storage_name}")
    assert rdub, f"No upload box in state for {storage_name} storage"
    url = f"{fixtures.config.rs_url}/upload-boxes/{rdub['id']}"
    headers = _headers(fixtures, full_name)

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
    fixtures: JointFixture,
    storage_name: str,
    state: str,
    full_name: str = "Data Steward",
    force: bool = False,
) -> Response:
    """Ask RS to move the upload box to the given state, as the given user."""
    box = _read_stable_box(fixtures, storage_name, full_name)
    assert box["state"] != state, f"The {storage_name} upload box is {state} already"
    url = f"{fixtures.config.rs_url}/upload-boxes/{box['id']}"
    data: dict[str, Any] = {"version": box["version"], "state": state}
    if force:
        data["force"] = True
    return fixtures.http.patch(url, headers=_headers(fixtures, full_name), json=data)


def _list_uploads(fixtures: JointFixture, storage_name: str) -> list[dict[str, Any]]:
    """Return every file upload RS lists for the box of the given storage."""
    rdub = fixtures.state.get_state(f"rdub_{storage_name}")
    assert rdub, f"No upload box in state for {storage_name} storage"
    url = f"{fixtures.config.rs_url}/upload-boxes/{rdub['id']}/uploads"
    response = fixtures.http.get(
        url, headers=_headers(fixtures), params={"limit": 1000}
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
    fixtures: JointFixture, alias: str, timeout: float = 180
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


def _run_batch_upload(
    fixtures: JointFixture,
    storage_name: str,
    file_info: list[tuple[str, Path]],
    sabotage: bool,
) -> None:
    """Upload the given files again, optionally sabotaging each one as it starts.

    The connector runs alongside the test rather than to completion, because the
    files can only be sabotaged while their uploads are being initiated. Its output
    goes to a file rather than a pipe, which would deadlock the upload once its
    buffer filled up.
    """
    connector = fixtures.connector
    connector.config.file_metadata_dir.mkdir(exist_ok=True)
    upload_token = fixtures.state.get_state(f"upload token for {storage_name}")
    assert upload_token, f"No upload token found for {storage_name}"

    tsv_path = write_upload_tsv(file_info, connector.config.work_dir)
    cmd = ["ghga-connector", "batch-upload", "--tsv", str(tsv_path), "--overwrite"]
    log_path = connector.config.work_dir / "requeue_upload.log"
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

            if sabotage:
                for alias, _ in file_info:
                    _seed_fis_file(fixtures, _wait_for_init_upload(fixtures, alias))

            process.wait(timeout=600)
        except BaseException:
            process.kill()
            process.wait()
            raise

    output = log_path.read_text(encoding="utf-8")
    print(output)
    assert "Successfully uploaded" in output, f"The connector failed:\n{output}"


@given(parse('the data upload box for "{storage_name}" storage is unlocked'))
def unlock_upload_box(storage_name: str, fixtures: JointFixture):
    """Move the upload box back to 'open' so its files can be replaced."""
    box = _read_stable_box(fixtures, storage_name)
    if box["state"] == "open":
        return
    response = _set_box_state(fixtures, storage_name, "open")
    assert response.status_code == 204, f"{response.status_code}: {response.text}"


@when(
    parse(
        'the three largest files of dataset "{dataset_alias}" are deleted from "{storage_name}" storage'
    )
)
def delete_largest_files(
    dataset_alias: str,
    storage_name: str,
    fixtures: JointFixture,
    file_fixture: dict[str, FileBatch],
):
    """Delete the biggest files of the dataset so they can be uploaded again.

    The biggest files take the longest to upload, which leaves the widest window for
    seeding FIS while each upload is still being initiated.
    """
    largest = sorted(
        file_fixture[dataset_alias].file_info,
        key=lambda info: info[1].stat().st_size,
        reverse=True,
    )[: len(ORDINALS)]

    rdub = fixtures.state.get_state(f"rdub_{storage_name}")
    headers = _headers(fixtures)
    targets: dict[str, dict[str, Any]] = {}
    for ordinal, (alias, file_path) in zip(ORDINALS, largest, strict=True):
        upload = _find_upload(fixtures, storage_name, alias)
        assert upload, f"No file upload listed for alias {alias!r}"
        url = (
            f"{fixtures.config.rs_url}/upload-boxes/{rdub['id']}/uploads/{upload['id']}"
        )
        response = fixtures.http.delete(url, headers=headers)
        assert response.status_code == 204, f"{response.status_code}: {response.text}"
        targets[ordinal] = {
            "alias": alias,
            "file_path": str(file_path),
            "storage_name": storage_name,
            "deleted_id": upload["id"],
        }

    fixtures.state.set_state(TARGETS_STATE, targets)


@when(
    parse(
        'those files are uploaded to "{storage_name}" storage with corrupted checksums'
    )
)
def upload_files_with_corrupted_checksums(storage_name: str, fixtures: JointFixture):
    """Upload the files again and make FIS expect checksums they cannot match."""
    targets = _targets(fixtures)
    file_info = [
        (targets[ordinal]["alias"], Path(targets[ordinal]["file_path"]))
        for ordinal in ORDINALS
    ]
    _run_batch_upload(fixtures, storage_name, file_info, sabotage=True)


@when(parse('the "{ordinal}" file is uploaded to "{storage_name}" storage again'))
def upload_file_again(ordinal: str, storage_name: str, fixtures: JointFixture):
    """Upload one of the files again, this time without touching its checksum."""
    target = _target(fixtures, ordinal)
    file_info = [(target["alias"], Path(target["file_path"]))]
    _run_batch_upload(fixtures, storage_name, file_info, sabotage=False)


@then(
    parse(
        'the "{ordinal}" file is listed as "{expected_state}" within "{seconds:d}" seconds'
    )
)
def check_file_state(
    ordinal: str, expected_state: str, seconds: int, fixtures: JointFixture
):
    """Wait for RS to list the given file in the expected state."""
    upload = _wait_for_file(
        fixtures,
        ordinal,
        lambda state: state == expected_state,
        expected_state,
        seconds,
    )
    fields = {"file_id": upload["id"]}
    # The inbox object ID has to be kept: once the file is interrogated,
    # the record points at the object in the interrogation bucket instead.
    if expected_state == "failed_interrogation":
        fields["inbox_object_id"] = upload["object_id"]
    _remember(fixtures, ordinal, **fields)


@then(
    parse(
        'the "{ordinal}" file has reached the "{expected_state}" state'
        ' within "{seconds:d}" seconds'
    )
)
def check_file_progress(
    ordinal: str, expected_state: str, seconds: int, fixtures: JointFixture
):
    """Wait for RS to list the given file in the expected state or past it."""
    _wait_for_file(
        fixtures,
        ordinal,
        lambda state: has_reached(state, expected_state),
        f"{expected_state} or later",
        seconds,
    )


def _wait_for_file(
    fixtures: JointFixture,
    ordinal: str,
    accept: Callable[[str], bool],
    expected: str,
    seconds: int,
) -> dict[str, Any]:
    """Poll RS until it lists the given file in an accepted state, and return it."""
    target = _target(fixtures, ordinal)
    alias, storage_name = target["alias"], target["storage_name"]
    deadline = time.monotonic() + seconds
    upload = None
    while time.monotonic() < deadline:
        upload = _find_upload(fixtures, storage_name, alias)
        if upload and accept(upload["state"]):
            return upload
        time.sleep(0.5)
    raise AssertionError(
        f"File {alias!r} is not {expected!r} after {seconds} seconds: {upload}"
    )


@then(parse('the "{ordinal}" file reports why it failed'))
def check_failure_reason(ordinal: str, fixtures: JointFixture):
    """Assert the file carries the reason the interrogation gave."""
    target = _target(fixtures, ordinal)
    upload = _find_upload(fixtures, target["storage_name"], target["alias"])
    assert upload and upload.get("failure_reason"), (
        f"No failure reason on the failed file: {upload}"
    )


@then(parse('the "{ordinal}" file no longer reports why it failed'))
def check_failure_reason_cleared(ordinal: str, fixtures: JointFixture):
    """Assert the requeue cleared the failure reason, which archival insists on."""
    target = _target(fixtures, ordinal)
    upload = _find_upload(fixtures, target["storage_name"], target["alias"])
    assert upload and not upload.get("failure_reason"), (
        f"The failure reason survived the requeue: {upload}"
    )


@then(parse('FIS holds a failed interrogation report for the "{ordinal}" file'))
def check_failure_report(ordinal: str, fixtures: JointFixture):
    """Assert FIS stored the report that the requeue has to discard."""
    file_id = _target(fixtures, ordinal)["file_id"]
    report = fixtures.mongo.wait_for_document(
        db_name=fixtures.config.fis_db_name,
        collection_name=fixtures.config.fis_reports_collection,
        query={"_id": file_id},
        timeout=30,
        interval=0.5,
    )
    assert report and report["passed"] is False, (
        f"FIS holds no failed interrogation report for file {file_id}: {report}"
    )


@then(parse('the interrogation report for the "{ordinal}" file has been discarded'))
def check_report_discarded(ordinal: str, fixtures: JointFixture):
    """Assert FIS dropped the report of the interrogation that failed.

    Paired with the step that asserts the report was there to begin with, since
    waiting for a document to disappear passes on one that never existed. Only the
    failed report counts: the retry may already have stored a passing one.
    """
    file_id = _target(fixtures, ordinal)["file_id"]
    removed = fixtures.mongo.wait_for_removal(
        db_name=fixtures.config.fis_db_name,
        collection_name=fixtures.config.fis_reports_collection,
        query={"_id": file_id, "passed": False},
        timeout=30,
        interval=0.5,
    )
    assert removed, f"FIS still holds a failed interrogation report for file {file_id}"


@then(parse('the "{ordinal}" file is marked as removable in the interrogation service'))
def check_file_removable(ordinal: str, fixtures: JointFixture):
    """Assert the deletion reached FIS, which releases the file for cleanup.

    FIS keeps its record of a cancelled file and flips `can_remove`, which is what
    lets DHFS clean up after it.
    """
    file_id = _target(fixtures, ordinal)["file_id"]
    deadline = time.monotonic() + 60
    document = None
    while time.monotonic() < deadline:
        document = fixtures.mongo.find_document(
            db_name=fixtures.config.fis_db_name,
            collection_name=fixtures.config.fis_files_collection,
            query={"_id": file_id},
        )
        if document and document.get("can_remove"):
            return
        time.sleep(0.5)
    raise AssertionError(f"FIS does not consider file {file_id} removable: {document}")


@then(
    parse(
        'the object of the "{ordinal}" file is still in the "{bucket}" bucket of "{storage_name}" storage'
    )
)
def check_object_kept(
    ordinal: str, bucket: str, storage_name: str, fixtures: JointFixture
):
    """Assert the failed file's object was kept, so no second upload is needed."""
    storage_config = fixtures.s3.get_storage_config(storage_name)
    object_id = _target(fixtures, ordinal)["inbox_object_id"]
    assert fixtures.s3.does_object_exist(
        storage_alias=storage_config.storage_alias,
        bucket=getattr(storage_config.buckets, bucket),
        object_id=object_id,
    ), f"{object_id} is gone from the {bucket} bucket of {storage_name} storage"


@then(
    parse(
        'the object of the "{ordinal}" file is gone from the "{bucket}" bucket of "{storage_name}" storage'
    )
)
def check_object_removed(
    ordinal: str, bucket: str, storage_name: str, fixtures: JointFixture
):
    """Assert the object was cleaned up once the file was resolved."""
    storage_config = fixtures.s3.get_storage_config(storage_name)
    object_id = _target(fixtures, ordinal)["inbox_object_id"]
    assert not fixtures.s3.does_object_exist(
        storage_alias=storage_config.storage_alias,
        bucket=getattr(storage_config.buckets, bucket),
        object_id=object_id,
    ), f"{object_id} is still in the {bucket} bucket of {storage_name} storage"


@then(parse('the upload box for "{storage_name}" storage holds "{count:d}" files'))
def check_box_file_count(count: int, storage_name: str, fixtures: JointFixture):
    """Assert the box statistics followed the deletion."""
    box = _read_stable_box(fixtures, storage_name)
    assert box["file_count"] == count, (
        f"Expected {count} files in the {storage_name} box, got {box['file_count']}"
    )


@when(
    parse('"{full_name}" requeues the "{ordinal}" file in "{storage_name}" storage'),
    target_fixture="response",
)
def requeue_failed_file(
    full_name: str, ordinal: str, storage_name: str, fixtures: JointFixture
) -> Response:
    """Ask RS to requeue a file, which only a Data Steward may do."""
    rdub = fixtures.state.get_state(f"rdub_{storage_name}")
    file_id = _target(fixtures, ordinal)["file_id"]
    url = (
        f"{fixtures.config.rs_url}/rpc/upload-boxes/{rdub['id']}"
        f"/uploads/{file_id}/requeue"
    )
    return fixtures.http.post(url, headers=_headers(fixtures, full_name))


@when(parse('I open the upload box for "{storage_name}" storage in the portal'))
def open_box_in_portal(storage_name: str, fixtures: JointFixture):
    """Open the details page of the upload box in the Upload Box Manager."""
    rdub = fixtures.state.get_state(f"rdub_{storage_name}")
    assert rdub, f"No upload box in state for {storage_name} storage"
    page = fixtures.playwright.page
    url = fixtures.config.data_portal_url.rstrip("/")
    page.goto(f"{url}/upload-box-manager/{rdub['id']}")
    expect(page).to_have_title("Upload Box Details | GHGA Data Portal")


@then(parse('the "{ordinal}" file is offered a retry in the portal'))
def check_retry_offered(ordinal: str, fixtures: JointFixture):
    """Check that a failed file can be requeued from the portal."""
    page = fixtures.playwright.page
    alias = _target(fixtures, ordinal)["alias"]
    expect(_file_row(page, alias)).to_contain_text(
        "re-encryption failed", timeout=UI_TIMEOUT
    )
    expect(_retry_button(page, alias)).to_be_visible()


@then("the portal offers to retry all failed re-encryptions")
def check_retry_all_offered(fixtures: JointFixture):
    """Check the whole-box retry, shown only once the complete file list has loaded."""
    expect(_retry_all_button(fixtures.playwright.page)).to_be_visible(
        timeout=UI_TIMEOUT
    )


@then("the portal no longer offers to retry all failed re-encryptions")
def check_retry_all_gone(fixtures: JointFixture):
    """Check the whole-box retry is gone once no file is waiting for a retry."""
    expect(_retry_all_button(fixtures.playwright.page)).to_have_count(0)


@when(parse('I retry the re-encryption of the "{ordinal}" file in the portal'))
def retry_in_portal(ordinal: str, fixtures: JointFixture):
    """Requeue a failed file with its retry button and confirm the dialog."""
    page = fixtures.playwright.page
    target = _target(fixtures, ordinal)
    alias = target["alias"]
    _retry_button(page, alias).click()

    dialog = page.get_by_role("dialog")
    expect(dialog).to_contain_text("Retry re-encryption?")
    expect(dialog).to_contain_text(alias)
    path = f"/uploads/{target['file_id']}/requeue"
    with page.expect_response(
        lambda response: (
            response.request.method == "POST" and response.url.endswith(path)
        ),
        timeout=UI_TIMEOUT,
    ) as response_info:
        dialog.get_by_role("button", name="Retry", exact=True).click()
    response = response_info.value
    assert response.status == 204, f"{response.status}: {response.text()}"


@when(
    "I retry all failed re-encryptions in the portal",
    target_fixture="requeue_result",
)
def retry_all_in_portal(fixtures: JointFixture) -> dict[str, list[str]]:
    """Requeue every failed file of the box and return what RS answered."""
    page = fixtures.playwright.page
    _retry_all_button(page).click()

    dialog = page.get_by_role("dialog")
    expect(dialog).to_contain_text("Retry all failed re-encryptions?")
    with page.expect_response(
        lambda response: (
            response.request.method == "POST"
            and re.search(r"/rpc/upload-boxes/[^/]+/requeue$", response.url) is not None
        ),
        timeout=UI_TIMEOUT,
    ) as response_info:
        dialog.get_by_role("button", name="Retry all").click()
    response = response_info.value
    assert response.status == 200, f"{response.status}: {response.text()}"
    return response.json()


@then(parse('the portal has requeued only the "{ordinal}" file'))
def check_requeue_result(
    ordinal: str, fixtures: JointFixture, requeue_result: dict[str, list[str]]
):
    """Check that the whole-box requeue picked exactly the one failed file."""
    file_id = _target(fixtures, ordinal)["file_id"]
    assert requeue_result == {"requeued": [file_id], "skipped": []}, requeue_result


@then(
    parse(
        'the portal reports that the "{ordinal}" file has been queued for re-encryption'
    )
)
def check_requeue_reported(ordinal: str, fixtures: JointFixture):
    """Check the notification confirming the requeue."""
    alias = _target(fixtures, ordinal)["alias"]
    expect(fixtures.playwright.page.locator("app-custom-snack-bar")).to_contain_text(
        f'The file "{alias}" has been queued for re-encryption.'
    )


@then(parse('the portal reports "{message}"'))
def check_portal_message(message: str, fixtures: JointFixture):
    """Check the notification the portal shows."""
    expect(fixtures.playwright.page.locator("app-custom-snack-bar")).to_contain_text(
        message
    )


@then(parse('the "{ordinal}" file is shown as "{status}" in the portal'))
def check_status_in_portal(ordinal: str, status: str, fixtures: JointFixture):
    """Check the status the portal shows for a file, which no longer needs a retry."""
    page = fixtures.playwright.page
    alias = _target(fixtures, ordinal)["alias"]
    expect(_file_row(page, alias)).to_contain_text(status)
    expect(_retry_button(page, alias)).to_have_count(0)


@when(
    parse('"{full_name}" deletes the "{ordinal}" file from "{storage_name}" storage'),
    target_fixture="response",
)
def delete_failed_file(
    full_name: str, ordinal: str, storage_name: str, fixtures: JointFixture
) -> Response:
    """Delete a failed file, the other way a Data Steward can resolve one."""
    rdub = fixtures.state.get_state(f"rdub_{storage_name}")
    file_id = _target(fixtures, ordinal)["file_id"]
    url = f"{fixtures.config.rs_url}/upload-boxes/{rdub['id']}/uploads/{file_id}"
    return fixtures.http.delete(url, headers=_headers(fixtures, full_name))


@when(
    parse('"{full_name}" locks the data upload box for "{storage_name}" storage'),
    target_fixture="response",
)
def lock_upload_box(full_name: str, storage_name: str, fixtures: JointFixture):
    """Lock the upload box, which is refused while a file needs attention."""
    return _set_box_state(fixtures, storage_name, "locked", full_name)


@when(
    parse('"{full_name}" force-locks the data upload box for "{storage_name}" storage'),
    target_fixture="response",
)
def force_lock_upload_box(full_name: str, storage_name: str, fixtures: JointFixture):
    """Lock the upload box anyway, which is what `force` is for."""
    return _set_box_state(fixtures, storage_name, "locked", full_name, force=True)


@when(
    parse(
        '"{full_name}" tries to archive the data upload box for "{storage_name}" storage'
    ),
    target_fixture="response",
)
def try_to_archive_upload_box(
    full_name: str, storage_name: str, fixtures: JointFixture
):
    """Attempt to archive the box while it still holds files that failed."""
    return _set_box_state(fixtures, storage_name, "archived", full_name)


@then("the response names all failed files as needing attention")
def check_files_need_attention(fixtures: JointFixture, response: Response):
    """Assert the refusal names the files a Data Steward has to resolve.

    RS reads the file states from UCS rather than its own copy, so this is where
    the two services have to agree on what a blocking file is.
    """
    need_attention = response.json()["data"]["need_attention"]
    expected = {_target(fixtures, ordinal)["file_id"] for ordinal in ORDINALS}
    assert set(need_attention) == expected, (
        f"Expected {sorted(expected)} to need attention, got {sorted(need_attention)}"
    )
