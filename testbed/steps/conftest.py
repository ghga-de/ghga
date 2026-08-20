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

"""Shared steps and fixtures"""

import os
import re
import subprocess
from pathlib import Path
from time import sleep
from typing import Any, NamedTuple

from fixtures import (  # noqa: RUF100
    Config,
    ConnectorFixture,
    DskFixture,
    HttpClient,
    JointFixture,
    KafkaFixture,
    MongoFixture,
    PlaywrightFixture,
    Response,
    S3Fixture,
    StateManager,
    StateStorage,
    VaultFixture,
    auth_fixture,
    config_fixture,
    connector_fixture,
    dsk_fixture,
    file_fixture,
    http_fixture,
    iva_fixture,
    joint_fixture,
    kafka_fixture,
    mongo_fixture,
    playwright_fixture,
    s3_fixture,
    state_fixture,
    state_manager_fixture,
    vault_fixture,
)
from pytest import StashKey, fixture, hookimpl, mark
from pytest_bdd import (  # noqa: RUF100
    given,
    scenarios,
    then,
    when,
)

from steps.conftest_1x import *  # noqa: F403
from steps.conftest_2x import *  # noqa: F403
from steps.conftest_5x import *  # noqa: F403
from steps.utils import (
    EXPECTED_NOTIFICATIONS,
    Notification,
    parse,
    parse_notifications,
    reset_user_token_counter,
)

# --- Playwright tracing (opt-in, debugging only) -------------------------------------
# A trace is the headless equivalent of watching the browser — `playwright show-trace
# <file>` replays the run action by action with the DOM, network and console at each
# step, so a failure can be inspected after the fact instead of reproduced.
#
# This is a debugging aid, not part of the suite: it stays off unless TB_TRACE is set,
# and even then only arms for browser tests (the @frontend tag). A default run therefore
# pays nothing, and the tests that never touch a browser never launch one.
#
#   TB_TRACE=1 just testbed -m frontend     traces kept for failed tests only
#   TB_TRACE=all just testbed -m frontend   traces kept for every browser test
#
# `all` is worth the disk: the browser context is shared for the whole session, so a
# failure is often caused by a test that passed. Traces land in testbed/.traces, or in
# TB_TRACE_DIR; the directory is emptied at the start of each traced run so what is left
# always describes the run you just did.
_TRACE_MODE = os.environ.get("TB_TRACE", "").strip().lower()
TRACE_ENABLED = _TRACE_MODE not in ("", "0", "false", "no", "off")
TRACE_ALL = _TRACE_MODE == "all"
TRACE_DIR = Path(
    os.environ.get("TB_TRACE_DIR") or Path(__file__).resolve().parent.parent / ".traces"
)

_REPORT_KEY = StashKey[dict]()


@hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    """Stash each phase's report so the tracing fixture can see the outcome."""
    report = yield
    if TRACE_ENABLED:
        item.stash.setdefault(_REPORT_KEY, {})[report.when] = report.failed
    return report


@fixture(scope="session")
def playwright_tracing(playwright: PlaywrightFixture):
    """Arm tracing on the browser context, on first use by a traced test."""
    if TRACE_DIR.is_dir():
        for stale in TRACE_DIR.glob("*.zip"):
            stale.unlink()  # traces from an earlier run would only mislead
    tracing = playwright.context.tracing
    tracing.start(screenshots=True, snapshots=True, sources=True)
    yield tracing
    tracing.stop()


@fixture(autouse=True)
def playwright_trace(request):
    """Record one trace chunk per browser test, keeping the ones worth looking at.

    Autouse, but inert unless tracing was asked for and this is a browser test. The
    Playwright fixtures are requested lazily inside that branch, so an untraced run
    never pulls a browser in through this fixture.
    """
    if not (TRACE_ENABLED and request.node.get_closest_marker("frontend")):
        yield
        return
    tracing = request.getfixturevalue("playwright_tracing")
    tracing.start_chunk(title=request.node.name)
    try:
        yield
    finally:
        failed = any(request.node.stash.get(_REPORT_KEY, {}).values())
        if failed or TRACE_ALL:
            TRACE_DIR.mkdir(parents=True, exist_ok=True)
            # keep the name filesystem-safe: scenario outlines carry [param] suffixes
            safe = re.sub(r"[^\w.-]+", "_", request.node.name)
            tracing.stop_chunk(path=str(TRACE_DIR / f"{safe}.zip"))
        else:
            tracing.stop_chunk()  # no path => discarded


class UserData(NamedTuple):
    """A container for user data."""

    id: str
    ext_id: str
    name: str
    title: str | None
    email: str


def get_user_data(name: str, fixtures: JointFixture) -> UserData:
    auth = fixtures.auth
    title, name = auth.split_title(name)
    sub = auth.get_sub(name)
    registered_users = fixtures.state.get_state("registered users") or {}
    user_id = registered_users.get(sub)
    assert user_id, f"{name} is not a registered user"
    email = auth.get_email(name)
    return UserData(user_id, sub, name, title, email)


@given(parse('I am registered as "{name}"'), target_fixture="user")
def registered_as_user(name: str, fixtures: JointFixture) -> UserData:
    return get_user_data(name, fixtures)


@given(parse('I am logged in as "{name}"'))
def login_as_user(name: str, fixtures: JointFixture):
    sub = fixtures.auth.get_sub(name)
    session = fixtures.auth.fetch_session(
        name=name, user_id=sub, state_store=fixtures.state
    )
    fixtures.auth.save_session(name=name, session=session, state_store=fixtures.state)


@given(parse('I am authenticated as "{full_name}"'))
def authenticate_user(full_name: str, fixtures: JointFixture):
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    assert session, f"No session found for {full_name}"
    response = fixtures.auth.authenticate(session=session, state_store=fixtures.state)
    assert response.status_code == 204, response.text

    # Update session cache with up-to-date session information from server
    login_as_user(full_name, fixtures)


@given(parse('the user "{name}" is logged out'))
def logout_as_user(name: str, fixtures: JointFixture):
    """Log out the user without knowing the login status on server.

    Sessions that are alive in the Auth Adapter need to be removed.
    In order to achieve this, the session is retrieved via login and used to logout.
    """
    sub = fixtures.auth.get_sub(name)
    session = fixtures.auth.get_saved_session(name=name, state_store=fixtures.state)
    if not session:
        print("No session found, creating a new one.")
        session = fixtures.auth.fetch_session(name=name, user_id=sub)
    reset_user_token_counter(sub, fixtures)
    fixtures.auth.auth_logout(session)
    fixtures.state.unset_state(f"session-{sub}")


@then(parse('the response status code is "{code:d}"'))
def check_status_code(code: int, response: Response):
    status_code = response.status_code
    assert status_code == code, f"{status_code}: {response.text}"


@given("the session store is empty")
def empty_session_store(fixtures: JointFixture):
    """Remove all states starting with "session" from the state storage"""
    fixtures.state.unset_state("session")


@given("the TOTP token store is empty")
def empty_totp_token_store(fixtures: JointFixture):
    """Remove all states starting with "totp-token" from the state storage"""
    fixtures.state.unset_state("totp-token-")


@given(parse('the user "{full_name}" has no TOTP token'))
def empty_totp_token_store_for_user(full_name: str, fixtures: JointFixture):
    """Remove states with "totp-token" for the user"""
    sub = fixtures.auth.get_sub(full_name)
    fixtures.state.unset_state(f"totp-token-{sub}")


# Global test bed state memory


def fetch_data_stewardship(fixtures: JointFixture) -> dict[str, Any]:
    """Fetch the data steward and the corresponding claim from the database."""
    state = {}
    claim = fixtures.mongo.find_document(
        fixtures.config.ums_db_name,
        fixtures.config.ums_claims_collection,
        {"visa_value": "data_steward@ghga.de"},
    )
    assert claim is not None, "no data steward claim found in the auth database"
    state["claim"] = claim
    user_id = claim["user_id"]
    user = fixtures.mongo.find_document(
        fixtures.config.ums_db_name,
        fixtures.config.ums_users_collection,
        {"_id": user_id},
    )
    assert user is not None, "no data steward found in the auth database"
    state["user"] = user
    user = fixtures.mongo.find_document(
        fixtures.config.nos_db_name,
        "users",
        {"_id": user_id},
    )
    assert user is not None, "no data steward found in the nos database"
    state["nos"] = user
    iva = fixtures.mongo.find_document(
        fixtures.config.ums_db_name,
        fixtures.config.ums_user_ivas_collection,
        {"user_id": user_id},
    )
    assert iva is not None, "no data steward IVA in the ums database"
    state["iva"] = iva
    return state


def restore_data_stewardship(state: dict[str, Any], fixtures: JointFixture) -> None:
    """Put the data steward and the corresponding claim back into the database."""
    user = state["user"]
    assert user
    fixtures.mongo.upsert_document(
        fixtures.config.ums_db_name,
        fixtures.config.ums_users_collection,
        user,
    )
    user = state["nos"]
    assert user
    fixtures.mongo.upsert_document(
        fixtures.config.nos_db_name,
        "users",
        user,
    )
    claim = state.get("claim")
    assert claim
    fixtures.mongo.upsert_document(
        fixtures.config.ums_db_name,
        fixtures.config.ums_claims_collection,
        claim,
    )
    iva = state.get("iva")
    assert iva
    fixtures.mongo.upsert_document(
        fixtures.config.ums_db_name,
        fixtures.config.ums_user_ivas_collection,
        iva,
    )
    registered_users = fixtures.state.get_state("registered users") or {}
    registered_users[state["user"]["ext_id"]] = state["user"]["_id"]
    fixtures.state.set_state("registered users", registered_users)


@given("we start on a clean slate")
def reset_state(fixtures: JointFixture):
    """Reset all state used by the Archive Test Bed."""
    fixtures.state.reset_state()  # empty state database
    fixtures.kafka.clear_topics()  # empty event queues
    fixtures.s3.empty_buckets()  # empty object storages
    saved_data_steward = fetch_data_stewardship(fixtures)
    fixtures.mongo.empty_databases()  # empty service databases
    restore_data_stewardship(saved_data_steward, fixtures)
    fixtures.dsk.reset_work_dir()  # reset local submission registry
    empty_mail_server(fixtures)  # reset mail server
    if not fixtures.config.black_box_mode:
        fixtures.vault.empty_secrets()  # empty secret storage


@given("no notification has been sent yet")
def reset_notifications(fixtures: JointFixture):
    """Delete all email notifications from the mail server."""
    fixtures.mongo.empty_databases("ns")
    empty_mail_server(fixtures)  # reset mail server


@given(parse('we have the state "{name}"'))
def assume_state_clause(name: str, state: StateStorage):
    value = state.get_state(name)
    assert value, f'The expected state "{name}" has not yet been set.'
    return value


@then(parse('set the state to "{name}"'))
def set_state_clause(name: str, state: StateStorage):
    state.set_state(name, True)


@then(parse('remove the state "{name}"'))
def unset_state_clause(name: str, state: StateStorage):
    state.unset_state(name)


def empty_mail_server(fixtures: JointFixture):
    """Delete all e-mails from mail server"""
    fixtures.http.delete(f"{fixtures.config.mail_url}/api/v1/messages")


@then(parse('I get only dataset "{ega_accession}" as search result'))
def check_study_search_result(ega_accession: str, response: Response):
    results = response.json()
    assert results["count"] == 1
    assert results["hits"][0]["content"]["ega_accession"] == ega_accession


@then(parse('I get "{count:d}" search results'))
def check_number_of_search_results(count: int, response: Response):
    results = response.json()
    assert results["count"] == count
    assert len(results["hits"]) == count


@then(parse('I get "{page_count:d}" out of "{total_count:d}" search results'))
def check_number_of_search_results_on_the_page(
    page_count: int, total_count: int, response: Response
):
    results = response.json()
    assert results["count"] == total_count
    assert len(results["hits"]) == page_count


@then(parse('the expected item count is "{count:d}"'))
def check_item_count_in_list(count: int, results: list):
    assert len(results) == count


@then(parse('the expected item count in response is "{count:d}"'))
def check_item_count_in_response(count: int, response: Response):
    results = response.json()

    if isinstance(results, list):
        check_item_count_in_list(count=count, results=results)

    if isinstance(results, dict):
        # Handle paginated responses like {'count': 0, 'boxes': []}
        for key in ("boxes", "results", "hits", "items"):
            if key in results:
                results = results[key]
                break
        else:
            assert False, f"No known list key found in response: {results}"
        assert len(results) == count


@then(
    parse('"{notification_type}" email was sent to "{full_name}"'),
    target_fixture="notification",
)
def check_email_sent_to(
    notification_type: str,
    full_name: str,
    fixtures: JointFixture,
    timeout: float = 15,
    interval: float = 0.1,
) -> Notification:
    """Validate e-mail notification.

    Wait for an e-mail to be received by the mail server. If it does not appear
    within the given timeout (in seconds), an AssertionError is raised.
    """
    notification_type = notification_type.lower().replace(" ", "_")
    url = f"{fixtures.config.mail_url}/api/v2/search"
    slept: float = 0
    subject = EXPECTED_NOTIFICATIONS.get(notification_type)
    assert subject, f"Undefined notification type: {notification_type}"
    if "(" in full_name:
        full_name, note = full_name.split("(", 1)
        full_name, note = full_name.rstrip(), note.rstrip(")")
    else:
        note = ""
    email = fixtures.auth.get_email(full_name)
    if "new email" in note:
        email = email.replace("@home", "@new-home")
    while slept < timeout:
        response = fixtures.http.get(
            url,
            headers={"accept": "application/json"},
            params={"kind": "containing", "query": subject},
            timeout=timeout,
        )  # not possible to filter by email and subject at the same time
        assert response.status_code == 200
        content = response.json()
        if content["count"] > 0:
            notifications = parse_notifications(content)
            notifications = sorted(notifications, key=lambda n: n.created_time)
            latest_notification = notifications[0]
            assert email in latest_notification.receiver
            assert latest_notification.is_recent()
            # delete the notification from the mail server as already seen
            url = f"{fixtures.config.mail_url}/api/v1/messages/{latest_notification.id}"
            response = fixtures.http.delete(url, timeout=timeout)
            assert response.status_code == 200
            return latest_notification
        sleep(interval)
        slept += interval
    assert False, f"An email notification was not received by {email}."


@then(
    parse(
        'the "{field}" of the request for dataset "{alias}" is present in the email subject'
    )
)
def check_field_in_email_subject(
    alias: str, field: str, fixtures: JointFixture, notification: Notification
):
    """Check that the value of the given field for the access request is present in the email subject."""
    assert notification, "No notification found for checking the email subject."
    _field = field.lower().replace(" ", "_")
    field_value = fixtures.state.get_state(f"access request {alias} {_field}")
    assert field_value in notification.subject, (
        f'The value "{field_value}" of field "{field}" is not present in the email subject "{notification.subject}".'
    )


@given("no file encryption secrets exist in the vault")
def reset_file_encryption_secrets(fixtures: JointFixture):
    """Reset the file encryption secrets in the vault."""
    if not fixtures.config.black_box_mode:
        fixtures.vault.empty_secrets()  # empty secret storage


@given("no access requests have been made yet")
def ars_database_is_empty(fixtures: JointFixture):
    assert not fixtures.state.get_state("is allowed to download")
    fixtures.mongo.empty_databases(
        fixtures.config.ars_db_name,
        collection_names=[fixtures.config.ars_access_requests_collection],
    )
    fixtures.state.unset_state("is allowed to download")
    fixtures.state.unset_state("access request")


@given("the claims repository is empty")
def claims_repository_is_empty(fixtures: JointFixture):
    """Remove all claims except for the data steward claim."""
    saved_data_steward = fetch_data_stewardship(fixtures)
    fixtures.mongo.empty_databases(
        fixtures.config.ums_db_name,
        collection_names=[
            fixtures.config.ums_claims_collection,
        ],
    )
    restore_data_stewardship(saved_data_steward, fixtures)


@then(parse('the command line message is "{expected_error_message}"'))
def check_cli_error(
    expected_error_message: str, completed_process: subprocess.CompletedProcess
):
    """Check that the CLI output contains the expected message.

    The tools are not standardized in their exit codes and outputs. E.g. DSKit does not
    exit with a non-zero code when a single ingest fails; instead, it returns a report.
    Therefore, neither a specific exit code nor stdout/stderr alone is reliable.

    This method only checks whether the expected message appears in stdout or stderr.
    """

    # Normalize minor formatting differences
    def _normalize_cli_text(text: str) -> str:
        """Normalize output for comparison."""
        text = re.sub(r"\x1b\[[0-9;]*m", "", text)  # remove ANSI
        text = text.replace("\r\n", "\n")
        text = "\n".join(line.rstrip() for line in text.split("\n"))
        text = re.sub(r"\s+", " ", text)  # Collapse whitespace
        return text.strip().lower()

    stderr = completed_process.stderr.strip()
    stdout = completed_process.stdout.strip()
    combined_output = f"{stdout}\n{stderr}"
    normalized_expected = _normalize_cli_text(expected_error_message)
    normalized_output = _normalize_cli_text(combined_output)

    assert (
        expected_error_message in combined_output
        or normalized_expected in normalized_output
    ), (
        f'Expected error message "{expected_error_message}" not found in output:\n'
        f"{combined_output}"
    )


@given("no file has been uploaded to the upload boxes yet")
def reset_upload_box_state(mongo: MongoFixture, state: StateStorage, config: Config):
    """Reset the state of the upload boxes in the database, without deleting them."""
    # Remove all upload entries
    mongo.empty_databases(config.ucs_db_name, collection_names=["fileUploads"])

    # Reset file upload box states in UCS
    ucs_boxes = mongo.find_documents(
        config.ucs_db_name,
        config.ucs_fub_collection,
        sloppy=True,
    )
    for box in ucs_boxes:
        updated_box = dict(box)
        updated_box["version"] = 0
        updated_box["file_count"] = 0
        updated_box["size"] = 0
        updated_box["state"] = "open"
        mongo.upsert_document(
            config.ucs_db_name,
            config.ucs_fub_collection,
            updated_box,
        )

    # Reset file upload box states in rs
    rs_boxes = mongo.find_documents(
        config.rs_db_name,
        config.rs_rdub_collection,
        sloppy=True,
    )
    for box in rs_boxes:
        updated_box = dict(box)
        updated_box["version"] = 0
        updated_box["file_upload_box_version"] = 0
        updated_box["file_count"] = 0
        updated_box["size"] = 0
        updated_box["state"] = "open"
        mongo.upsert_document(
            config.rs_db_name,
            config.rs_rdub_collection,
            updated_box,
        )


@given("I have an empty working directory for the GHGA connector")
def clean_connector_work_dir(connector: ConnectorFixture):
    connector.reset_work_dir()


@given("my Crypt4GH key pair has been stored in two key files")
def keys_are_made_available(connector: ConnectorFixture, config: Config):
    connector.store_keys(
        public_key=config.user_public_crypt4gh_key,
        private_key=config.user_private_crypt4gh_key,
    )
