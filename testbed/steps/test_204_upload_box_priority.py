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
#

"""Step definitions for the upload box priority list and the interrogation order"""

import json
import subprocess
from collections.abc import Generator
from datetime import datetime
from typing import Any
from uuid import uuid4

from fixtures.file import create_named_file
from ghga_service_commons.utils.utc_dates import now_as_utc
from pytest import fixture

from .conftest import (
    Config,
    JointFixture,
    Response,
    given,
    parse,
    scenarios,
    then,
    when,
)
from .conftest_2x import _session_headers, run_batch_upload

scenarios("../features/204_upload_box_priority.feature")

BOX_NAMES = ("first", "second")
FILES_PER_BOX = 2


def _box(fixtures: JointFixture, box_name: str) -> dict[str, Any]:
    """Get the upload box with the given name from the state."""
    assert box_name in BOX_NAMES, f"Unknown upload box: {box_name}"
    box = fixtures.state.get_state(f"rdub_{box_name}")
    assert box, f"No {box_name} upload box in state"
    return box


def _priority_url(fixtures: JointFixture) -> str:
    return f"{fixtures.config.rs_url}/upload-box-priority"


def _read_priority(fixtures: JointFixture, full_name: str) -> dict[str, Any]:
    """Read the upload box priority list."""
    response = fixtures.http.get(
        _priority_url(fixtures), headers=_session_headers(fixtures, full_name)
    )
    assert response.status_code == 200, f"{response.status_code}: {response.text}"
    return response.json()


def _box_ids(priority: dict[str, Any]) -> list[str]:
    """Get the box IDs of a priority list, highest priority first."""
    return [entry["research_data_upload_box_id"] for entry in priority["entries"]]


def _save_order(
    fixtures: JointFixture, full_name: str, *, version: int, box_ids: list[str]
) -> Response:
    """Save a new order of the upload boxes."""
    return fixtures.http.put(
        _priority_url(fixtures),
        headers=_session_headers(fixtures, full_name),
        json={"version": version, "box_ids": box_ids},
    )


def _saved_priority(fixtures: JointFixture) -> dict[str, Any]:
    """Get the priority list that the data steward saved."""
    saved = fixtures.state.get_state("saved upload box priority")
    assert saved, "No saved upload box priority in state"
    return saved


@when(
    parse('"{full_name}" creates the "{box_name}" upload box'),
    target_fixture="response",
)
def create_upload_box(
    full_name: str, box_name: str, fixtures: JointFixture
) -> Response:
    """Create an upload box in the primary storage and store it in the state."""
    assert box_name in BOX_NAMES, f"Unknown upload box: {box_name}"
    storage_alias = fixtures.s3.get_storage_config("primary").storage_alias
    headers = _session_headers(fixtures, full_name)
    url = f"{fixtures.config.rs_url}/upload-boxes"
    payload = {
        # RS rejects a title that another box has, so a rerun gets new titles
        "title": f"RDUB_priority_{box_name}_{uuid4().hex[:8]}",
        "description": f"The {box_name} box of the upload box priority test",
        "storage_alias": storage_alias,
        "max_size": fixtures.config.default_file_size * 10,
    }
    response = fixtures.http.post(url, headers=headers, json=payload)
    if response.status_code == 201:
        box = fixtures.http.get(f"{url}/{response.json()}", headers=headers).json()
        fixtures.state.set_state(f"rdub_{box_name}", box)
    return response


@when(
    parse(
        '"{full_name}" saves the priority list with the "{moved}" upload box'
        ' before the "{other}"'
    ),
    target_fixture="response",
)
def save_box_before_other(
    full_name: str, moved: str, other: str, fixtures: JointFixture
) -> Response:
    """Move one box before another in the priority list and save the order."""
    priority = _read_priority(fixtures, full_name)
    box_ids = _box_ids(priority)
    moved_id, other_id = _box(fixtures, moved)["id"], _box(fixtures, other)["id"]
    box_ids.remove(moved_id)
    box_ids.insert(box_ids.index(other_id), moved_id)

    response = _save_order(
        fixtures, full_name, version=priority["version"], box_ids=box_ids
    )
    fixtures.state.set_state("upload box priority before the save", priority)
    if response.status_code == 200:
        fixtures.state.set_state("saved upload box priority", response.json())
    return response


@then(
    parse('the saved priority list has the "{moved}" upload box before the "{other}"')
)
def check_box_before_other(moved: str, other: str, fixtures: JointFixture):
    """Check the order of two boxes in the saved priority list."""
    box_ids = _box_ids(_saved_priority(fixtures))
    moved_id, other_id = _box(fixtures, moved)["id"], _box(fixtures, other)["id"]
    assert box_ids.index(moved_id) < box_ids.index(other_id), (
        f"Expected the {moved} box {moved_id} before the {other} box {other_id}"
        f" in {box_ids}"
    )


@then("the saved priority list has a new version")
def check_new_version(fixtures: JointFixture):
    """Check that the save incremented the version."""
    before = fixtures.state.get_state("upload box priority before the save")
    saved = _saved_priority(fixtures)
    assert saved["version"] == before["version"] + 1, (
        f"Expected version {before['version'] + 1}, got {saved['version']}"
    )


@then(
    parse(
        '"{full_name}" changed and reordered the saved priority list at the same time'
    )
)
def check_changed_and_reordered(full_name: str, fixtures: JointFixture):
    """Check that a save names the steward in both pairs of change fields."""
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    assert session and session.user_id, f"No user ID found for {full_name}"
    saved = _saved_priority(fixtures)
    assert saved["changed_by"] == saved["reordered_by"] == session.user_id, saved
    assert saved["last_changed"] == saved["reordered_at"], saved


@then("FIS stores the saved version of the priority list")
def check_fis_priority_version(fixtures: JointFixture):
    """Check that FIS receives the saved list through the outbox event."""
    version = _saved_priority(fixtures)["version"]
    document = fixtures.mongo.wait_for_document(
        db_name=fixtures.config.fis_db_name,
        collection_name=fixtures.config.fis_priority_collection,
        # The fixed ID is no UUID, so it must not be mapped to one
        query={"_id": "global", "version": version},
        timeout=60,
        interval=0.5,
        extend_mapping=False,
    )
    assert document is not None, f"FIS did not store version {version} in time"


@when(
    parse(
        '"{full_name}" saves the priority list again with the version it read before'
    ),
    target_fixture="response",
)
def save_on_old_version(full_name: str, fixtures: JointFixture) -> Response:
    """Save the saved order again, but on the version it was based on."""
    before = fixtures.state.get_state("upload box priority before the save")
    return _save_order(
        fixtures,
        full_name,
        version=before["version"],
        box_ids=_box_ids(_saved_priority(fixtures)),
    )


@when(
    parse('"{full_name}" saves the priority list without the "{box_name}" upload box'),
    target_fixture="response",
)
def save_without_box(full_name: str, box_name: str, fixtures: JointFixture) -> Response:
    """Save an order that leaves out a box that is not archived."""
    saved = _saved_priority(fixtures)
    box_id = _box(fixtures, box_name)["id"]
    box_ids = [other for other in _box_ids(saved) if other != box_id]
    return _save_order(fixtures, full_name, version=saved["version"], box_ids=box_ids)


@when(
    parse('"{full_name}" saves the priority list with an unknown box'),
    target_fixture="response",
)
def save_with_unknown_box(full_name: str, fixtures: JointFixture) -> Response:
    """Save an order that holds a box that does not exist."""
    saved = _saved_priority(fixtures)
    box_ids = [*_box_ids(saved), str(uuid4())]
    return _save_order(fixtures, full_name, version=saved["version"], box_ids=box_ids)


@when(
    parse(
        '"{full_name}" saves the priority list with the "{box_name}" upload box twice'
    ),
    target_fixture="response",
)
def save_with_box_twice(
    full_name: str, box_name: str, fixtures: JointFixture
) -> Response:
    """Save an order that holds a box twice."""
    saved = _saved_priority(fixtures)
    box_ids = [*_box_ids(saved), _box(fixtures, box_name)["id"]]
    return _save_order(fixtures, full_name, version=saved["version"], box_ids=box_ids)


@when(
    parse('"{full_name}" saves the stored priority list'),
    target_fixture="response",
)
def save_stored_order(full_name: str, fixtures: JointFixture) -> Response:
    """Save the stored order unchanged."""
    priority = _read_priority(fixtures, full_name)
    return _save_order(
        fixtures, full_name, version=priority["version"], box_ids=_box_ids(priority)
    )


@then("the priority list keeps the saved version")
def check_version_kept(fixtures: JointFixture, response: Response):
    """Check that a save without changes writes nothing."""
    saved = _saved_priority(fixtures)
    assert response.json() == saved, f"Expected {saved}, got {response.json()}"


@when(
    parse('"{full_name}" grants "{user_name}" access to the "{box_name}" upload box'),
    target_fixture="response",
)
def grant_upload_access(
    full_name: str, user_name: str, box_name: str, fixtures: JointFixture
) -> Response:
    """Grant the user access to the upload box for a year."""
    _, name = fixtures.auth.split_title(user_name)
    registered_users = fixtures.state.get_state("registered users") or {}
    user_id = registered_users.get(fixtures.auth.get_sub(name))
    iva = fixtures.state.get_state("Phone iva")
    assert user_id and iva and iva["id"], f"No verified user {user_name} in state"

    valid_from = now_as_utc()
    payload = {
        "valid_from": valid_from.isoformat(),
        "valid_until": valid_from.replace(year=valid_from.year + 1).isoformat(),
        "user_id": user_id,
        "iva_id": iva["id"],
        "box_id": _box(fixtures, box_name)["id"],
    }
    return fixtures.http.post(
        f"{fixtures.config.rs_url}/upload-grants",
        headers=_session_headers(fixtures, full_name),
        json=payload,
    )


@when(
    parse(
        '"{full_name}" creates an upload work package for the "{box_name}" upload box'
    ),
    target_fixture="response",
)
def create_upload_work_package(
    full_name: str, box_name: str, fixtures: JointFixture
) -> Response:
    """Create an upload work package for the upload box."""
    data = {
        "type": "upload",
        "research_data_upload_box_id": _box(fixtures, box_name)["id"],
        "user_public_crypt4gh_key": fixtures.config.user_public_crypt4gh_key,
    }
    return fixtures.http.post(
        f"{fixtures.config.wps_url}/work-packages",
        headers=_session_headers(fixtures, full_name),
        json=data,
    )


@then(parse('the response contains an upload token for the "{box_name}" upload box'))
def store_upload_token(box_name: str, fixtures: JointFixture, response: Response):
    """Store the upload token of the work package in the state."""
    data = response.json()
    assert set(data) == {"id", "token", "expires"}, data
    fixtures.state.set_state(
        f"upload token for {box_name}", f"{data['id']}:{data['token']}"
    )


class PausedDhfs:
    """Pause the DHFS of a storage by scaling its Deployment down to no pod."""

    def __init__(self, config: Config):
        self._kubectl = ["kubectl", "--context", config.kube_context]
        self._deployments = config.dhfs_deployments
        self._paused: dict[str, int] = {}  # replicas by deployment

    def _run(self, *args: str, accept: str | None = None) -> str:
        """Run kubectl with the given arguments and return its output. A failure
        whose message holds `accept` counts as success.
        """
        completed = subprocess.run(  # nosec B603
            [*self._kubectl, *args],
            capture_output=True,
            check=False,
            encoding="utf-8",
            timeout=300,
        )
        accepted = accept is not None and accept in completed.stderr
        assert completed.returncode == 0 or accepted, (
            f"kubectl {' '.join(args)} failed: {completed.stderr}"
        )
        return completed.stdout.strip()

    def pause(self, storage_name: str) -> None:
        """Scale the DHFS of the storage down and wait until its pods are gone."""
        deployment = self._deployments[storage_name]
        replicas = self._run(
            "get", "deployment", deployment, "-o", "jsonpath={.spec.replicas}"
        )
        labels = json.loads(
            self._run(
                "get",
                "deployment",
                deployment,
                "-o",
                "jsonpath={.spec.selector.matchLabels}",
            )
        )
        selector = ",".join(f"{key}={value}" for key, value in labels.items())
        self._run("scale", "deployment", deployment, "--replicas=0")
        self._paused[deployment] = int(replicas)
        # A pod that is shutting down could still fetch a file. kubectl wait fails
        # if no pod matches, but then there is nothing to wait for either.
        self._run(
            "wait",
            "--for=delete",
            "pod",
            f"--selector={selector}",
            "--timeout=120s",
            accept="no matching resources found",
        )

    def resume(self) -> None:
        """Scale every paused DHFS back up and wait until it is ready."""
        while self._paused:
            deployment, replicas = self._paused.popitem()
            self._run("scale", "deployment", deployment, f"--replicas={replicas}")
            self._run("rollout", "status", "deployment", deployment, "--timeout=180s")


@fixture(name="paused_dhfs")
def paused_dhfs_fixture(config: Config) -> Generator[PausedDhfs]:
    """Pause DHFS on request, and resume it at the end of the scenario at the latest,
    so that a failed step does not leave it paused for the following features.
    """
    paused_dhfs = PausedDhfs(config)
    yield paused_dhfs
    paused_dhfs.resume()


@given(parse('the DHFS of the "{storage_name}" storage is paused'))
def pause_dhfs(storage_name: str, paused_dhfs: PausedDhfs):
    paused_dhfs.pause(storage_name)


@when(parse('the DHFS of the "{storage_name}" storage resumes'))
def resume_dhfs(paused_dhfs: PausedDhfs):
    paused_dhfs.resume()


@when(parse('two files are uploaded to the "{box_name}" upload box'))
def upload_two_files(box_name: str, fixtures: JointFixture):
    """Upload two small files to the upload box and store their IDs in the state."""
    box = _box(fixtures, box_name)
    upload_token = fixtures.state.get_state(f"upload token for {box_name}")
    assert upload_token, f"No upload token for the {box_name} upload box"
    target_dir = fixtures.connector.config.work_dir / f"priority_{box_name}"
    target_dir.mkdir(parents=True, exist_ok=True)
    aliases = [f"PRIORITY_{box_name.upper()}_{n}" for n in range(1, FILES_PER_BOX + 1)]
    file_info = []
    for alias in aliases:
        file_object = create_named_file(
            target_dir=target_dir,
            config=fixtures.config,
            name=f"{alias}.fastq.gz",
            alias=alias,
            file_size=fixtures.config.upload_part_size**2,
        )
        file_info.append((file_object.object_id, file_object.file_path))

    completed_upload = run_batch_upload(
        file_info=file_info, fixtures=fixtures, upload_token=upload_token
    )
    assert "Successfully uploaded" in completed_upload.stdout

    files = fixtures.mongo.wait_for_documents(
        db_name=fixtures.config.ucs_db_name,
        collection_name=fixtures.config.ucs_file_uploads_collection,
        query={"box_id": {"$uuid": box["file_upload_box_id"]}, "state": "inbox"},
        number=FILES_PER_BOX,
        timeout=60,
        interval=0.5,
    )
    assert files, f"UCS has not got the files of the {box_name} box in its inbox"
    assert {file["alias"] for file in files} == set(aliases), files
    file_ids = [file["_id"] for file in files]
    fixtures.state.set_state(f"files of the {box_name} upload box", file_ids)


def _fis_file(fixtures: JointFixture, file_id: str, **fields: Any) -> dict[str, Any]:
    """Wait for the FIS document of a file to have the given fields."""
    document = fixtures.mongo.wait_for_document(
        db_name=fixtures.config.fis_db_name,
        collection_name=fixtures.config.fis_files_collection,
        query={"_id": file_id, **fields},
        timeout=60,
        interval=0.5,
    )
    assert document is not None, f"FIS has no file {file_id} with {fields} in time"
    return document


@then("FIS stores the box of each file uploaded to the two boxes")
def check_fis_box_ids(fixtures: JointFixture):
    """Check that FIS knows the file upload box of each waiting file.

    FIS ranks a file by this box, so a file without it would come last.
    """
    for box_name in BOX_NAMES:
        box = _box(fixtures, box_name)
        for file_id in fixtures.state.get_state(f"files of the {box_name} upload box"):
            document = _fis_file(fixtures, file_id)
            assert document["box_id"] == box["file_upload_box_id"], document
            assert document["state"] == "inbox", document


def _interrogation_order(fixtures: JointFixture) -> list[str]:
    """Wait until DHFS has interrogated the files of both boxes, and return their IDs
    in the order of interrogation.
    """
    interrogated_at: dict[str, datetime] = {}
    for box_name in BOX_NAMES:
        for file_id in fixtures.state.get_state(f"files of the {box_name} upload box"):
            document = _fis_file(fixtures, file_id, state="interrogated")
            interrogated_at[file_id] = datetime.fromisoformat(document["state_updated"])
    return sorted(interrogated_at, key=interrogated_at.__getitem__)


@then(
    parse(
        'the files of the "{earlier}" upload box are interrogated before those of the'
        ' "{later}"'
    )
)
def check_box_order(earlier: str, later: str, fixtures: JointFixture):
    """Check that DHFS interrogated all files of one box before those of another."""
    order = _interrogation_order(fixtures)
    earlier_files = set(fixtures.state.get_state(f"files of the {earlier} upload box"))
    assert set(order[: len(earlier_files)]) == earlier_files, (
        f"Expected the files of the {earlier} box {earlier_files} before those of the"
        f" {later} box, got {order}"
    )


@then("the files of each of the two boxes are interrogated in the order of their IDs")
def check_order_within_boxes(fixtures: JointFixture):
    """Check that DHFS interrogated the files of each box in ascending ID order,
    which is how FIS sorts the files of one box.
    """
    order = _interrogation_order(fixtures)
    for box_name in BOX_NAMES:
        file_ids = fixtures.state.get_state(f"files of the {box_name} upload box")
        # The canonical UUID strings sort like the UUIDs that MongoDB compares
        in_order = [file_id for file_id in order if file_id in file_ids]
        assert in_order == sorted(file_ids), (
            f"Expected the files of the {box_name} box in ID order, got {in_order}"
        )
