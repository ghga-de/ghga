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

"""Step definitions for uploading and ingesting files with the datasteward-kit"""

from uuid import UUID

from ghga_service_commons.utils.utc_dates import now_as_utc

from .conftest import (
    Config,
    JointFixture,
    MongoFixture,
    Response,
    StateStorage,
    given,
    parse,
    scenarios,
    then,
    when,
)

scenarios("../features/200_upload_initiated.feature")

UPLOAD_VISA_TYPE = "https://www.ghga.de/GA4GH/VisaTypes/Upload/v1.0"


@given("no data upload boxes have been created yet")
def rs_database_is_empty(config: Config, mongo: MongoFixture, state: StateStorage):
    state.unset_state("rdub_")
    mongo.empty_databases(config.rs_db_name, collection_names=config.rs_rdub_collection)


@when(
    parse('"{full_name}" creates a data upload boxes for "{storage_name}" storage'),
    target_fixture="response",
)
def create_data_upload_box(
    full_name: str, storage_name: str, fixtures: JointFixture
) -> Response:
    """Create a data upload box for the specified storage scope."""
    assert storage_name in ["primary", "secondary"], f"Unknown storage: {storage_name}"
    storage_config = fixtures.s3.get_storage_config(storage_name)
    storage_alias = storage_config.storage_alias

    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    assert session, f"No session found for {full_name}"
    assert session.user_id, f"user_id is missing for {full_name}"

    url = f"{fixtures.config.rs_url}/upload-boxes"
    headers = fixtures.auth.headers(session=session)
    payload = {
        "title": f"RDUB_{storage_alias}",
        "description": f"RDUB_{storage_alias}",
        "storage_alias": storage_alias,
        "max_size": fixtures.config.default_file_size * 10,
    }
    return fixtures.http.post(url, headers=headers, json=payload)


@given(
    parse('a data upload box for "{storage_name}" storage has been created'),
    target_fixture="response",
)
def confirm_rdub_exists(storage_name: str, fixtures: JointFixture):
    """Ensure that a data upload box for the specified storage scope exists."""
    rdub = fixtures.state.get_state(f"rdub_{storage_name}")
    assert rdub, f"No data upload box found for storage '{storage_name}'"


@when(
    parse('"{full_name}" lists the access grants for "{user_name}"'),
    target_fixture="response",
)
def list_access_grants(
    full_name: str, user_name: str, fixtures: JointFixture
) -> Response:
    """List the access grants for the specified user."""
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    assert session, f"No session found for {full_name}"
    assert session.user_id, f"user_id is missing in {full_name} session"
    user_id = session.user_id

    url = f"{fixtures.config.rs_url}/upload-grants"
    headers = fixtures.auth.headers(session=session)
    params = {"user_id": user_id}
    return fixtures.http.get(url, headers=headers, params=params)


@when(
    parse(
        '"{full_name}" grants "{user_name}" access to upload box for "{storage_name}" storage'
    ),
    target_fixture="response",
)
def grant_user_access_to_upload_box(
    full_name: str, user_name: str, storage_name: str, fixtures: JointFixture
) -> Response:
    """Grant the specified user access to the data upload box for the specified storage scope."""
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    assert session, f"No session found for {full_name}"

    _, name = fixtures.auth.split_title(user_name)
    sub = fixtures.auth.get_sub(name)
    registered_users = fixtures.state.get_state("registered users") or {}
    user_id = registered_users.get(sub)

    iva = fixtures.state.get_state("Phone iva")
    assert iva["id"]

    rdub = fixtures.state.get_state(f"rdub_{storage_name}")

    url = f"{fixtures.config.rs_url}/upload-grants"
    headers = fixtures.auth.headers(session=session)
    valid_from = now_as_utc()
    valid_until = valid_from.replace(year=valid_from.year + 1)
    payload = {
        "valid_from": valid_from.isoformat(),
        "valid_until": valid_until.isoformat(),
        "user_id": user_id,
        "iva_id": iva["id"],
        "box_id": rdub["id"],
    }
    return fixtures.http.post(url, headers=headers, json=payload)


@when(
    parse('"{full_name}" lists grants for "{storage_name}" storage'),
    target_fixture="response",
)
def list_grants_for_storage(
    full_name: str, storage_name: str, fixtures: JointFixture
) -> Response:
    """List the access grants for the specified upload box."""
    assert storage_name in ["primary", "secondary"], f"Unknown storage: {storage_name}"
    rdub = fixtures.state.get_state(f"rdub_{storage_name}")
    assert rdub, f"No data upload box found for storage '{storage_name}'"

    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    assert session, f"No session found for {full_name}"
    assert session.user_id, f"user_id is missing for {full_name}"

    url = f"{fixtures.config.rs_url}/upload-grants"
    headers = fixtures.auth.headers(session=session)
    params = {"box_id": rdub["id"]}
    return fixtures.http.get(url, headers=headers, params=params)


@then(
    parse(
        'the upload claim for "{storage_name}" storage exists in the claims repository'
    )
)
def check_upload_claim_exists(fixtures: JointFixture, storage_name: str):
    """Check that the upload claim for the given storage exists in the claims repository."""
    rdub = fixtures.state.get_state(f"rdub_{storage_name}")
    assert rdub, f"No data upload box found for storage '{storage_name}'"

    grants = fixtures.mongo.wait_for_documents(
        fixtures.config.ums_db_name,
        fixtures.config.ums_claims_collection,
        {"visa_type": UPLOAD_VISA_TYPE},
    )
    assert grants

    visa_value = f"https://ghga.de/uploads/{rdub.get('id')}"

    claim = next(
        (grant for grant in grants if grant.get("visa_value") == visa_value), None
    )
    assert claim, (
        f"Upload claim for {storage_name} storage not found in claims repository"
    )


@when(
    parse(
        '"{full_name}" creates an extra data upload box for "{storage_name}" storage'
    ),
    target_fixture="response",
)
def create_extra_upload_box(
    full_name: str, storage_name: str, fixtures: JointFixture
) -> Response:
    """Create an additional, disposable upload box for testing deletion."""
    assert storage_name in ["primary", "secondary"], f"Unknown storage: {storage_name}"
    storage_alias = fixtures.s3.get_storage_config(storage_name).storage_alias

    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    assert session, f"No session found for {full_name}"
    assert session.user_id, f"user_id is missing for {full_name}"

    url = f"{fixtures.config.rs_url}/upload-boxes"
    headers = fixtures.auth.headers(session=session)
    payload = {
        "title": f"RDUB_{storage_alias}_extra",
        "description": "Disposable upload box for the deletion test",
        "storage_alias": storage_alias,
        "max_size": fixtures.config.default_file_size * 10,
    }
    return fixtures.http.post(url, headers=headers, json=payload)


@then("we have an extra data upload box")
def store_extra_upload_box_id(response: Response, fixtures: JointFixture):
    """Retrieve upload box from response, validate schema and store in state"""
    box_id = response.json()
    try:
        UUID(box_id, version=4)
    except (ValueError, TypeError) as e:
        raise AssertionError(f"'{box_id}' is not a valid UUID v4: {e}") from e

    # Store the extra upload box ID in state for later deletion
    fixtures.state.set_state("extra_rdub_id", box_id)


@when(
    parse('"{full_name}" deletes the extra data upload box'),
    target_fixture="response",
)
def delete_upload_box(
    full_name: str, response: Response, fixtures: JointFixture
) -> Response:
    """Delete the previously created, disposable upload box."""
    box_id = response.json()
    try:
        UUID(box_id, version=4)
    except (ValueError, TypeError) as e:
        raise AssertionError(f"'{box_id}' is not a valid UUID v4: {e}") from e

    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    assert session, f"No session found for {full_name}"

    # Fetch the current box version as the delete endpoint expects it.
    url = f"{fixtures.config.rs_url}/upload-boxes/{box_id}"
    headers = fixtures.auth.headers(session=session)
    box = fixtures.http.get(url, headers=headers).json()

    return fixtures.http.delete(
        url, headers=headers, params={"version": box["version"]}
    )


@then("the extra data upload box is no longer listed")
def check_box_not_listed(response: Response, fixtures: JointFixture):
    """Confirm the deleted box is absent from the retrieved list of boxes."""
    rdub_primary = fixtures.state.get_state("rdub_primary")
    rdub_secondary = fixtures.state.get_state("rdub_secondary")
    assert rdub_primary and rdub_secondary, (
        "Expected both primary and secondary upload boxes to be present in state"
    )
    expected_list = [rdub_primary["id"], rdub_secondary["id"]]

    # Check RS API to ensure only the expected boxes are returned
    boxes = response.json().get("boxes", [])
    actual_list = [box.get("id") for box in boxes]
    assert set(expected_list) == set(actual_list), (
        f"Expected upload boxes {expected_list}, but got {actual_list}"
    )

    # Check WPS collection: the deletion reaches WPS via an event, so the box
    # disappears asynchronously. Wait for the specific deleted box to be gone,
    # then confirm the two expected boxes remain.
    extra_id = fixtures.state.get_state("extra_rdub_id")
    assert extra_id, "No extra upload box id recorded to check for removal"
    removed = fixtures.mongo.wait_for_removal(
        fixtures.config.wps_db_name,
        fixtures.config.wps_rdub_collection,
        query={"_id": extra_id},
    )
    assert removed, (
        f"Extra upload box {extra_id} still present in WPS collection after deletion"
    )
