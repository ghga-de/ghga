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

"""Step definitions for testing independent verification addresses"""

import json
import re
import time
from datetime import timedelta

from fixtures.iva import IVA
from ghga_service_commons.utils.utc_dates import now_as_utc

from .conftest import (
    JointFixture,
    Response,
    given,
    parse,
    scenarios,
    then,
    when,
)

scenarios("../features/110_user_verification.feature")


# Types are case-sensitive as they are requested by the API
USER_IVAS = {
    "Phone": "+491710000001",
    "InPerson": "A person",
}


EXPECTED_SMS_BODY = {
    "phone": USER_IVAS["Phone"],
    "text": r"Your verification code is: [A-Z0-9]{6}",
    "sender_id": "GHGA",
}


@given(parse('all the IVAs of "{full_name}" are deleted'))
def remove_user_ivas(full_name: str, fixtures: JointFixture):
    """Retrieve the list of all IVAs and delete them"""
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    assert session, "User session not found"
    assert session.user_id, "User ID not found"
    headers = fixtures.auth.headers(session=session)
    results = fixtures.iva.retrieve(session.user_id, headers)
    ivas_to_delete = [iva["id"] for iva in results]
    fixtures.iva.delete(ivas_to_delete, session.user_id, headers)


@when(parse('"{full_name}" adds "{iva_type}" as an IVA'), target_fixture="iva")
def user_adds_an_iva(full_name: str, iva_type: str, fixtures: JointFixture) -> IVA:
    """Add an IVA to the user account"""
    iva_value = USER_IVAS.get(iva_type)
    assert iva_value, (
        f"Incompatible IVA: {iva_type}. Available types: {USER_IVAS.keys()}]"
    )
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    assert session, "User session not found"
    assert session.user_id, "User ID not found"
    headers = fixtures.auth.headers(session=session)
    iva = fixtures.iva.create(
        iva_type=iva_type, iva_value=iva_value, user_id=session.user_id, headers=headers
    )
    fixtures.state.set_state(f"{iva_type} iva", iva.model_dump())
    return iva


@when(
    parse('"{full_name}" retrieves the list of "{iva_state}" IVAs'),
    target_fixture="results",
)
def list_user_ivas(full_name: str, iva_state: str, fixtures: JointFixture):
    """Retrieve the list of IVAs for the user"""
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    assert session, "User session not found"
    assert session.user_id, "User ID not found"
    headers = fixtures.auth.headers(session=session)
    ivas = fixtures.iva.retrieve(session.user_id, headers)
    if iva_state.lower() != "all":
        ivas = [iva for iva in ivas if iva["state"].lower() == iva_state.lower()]
    return ivas


@when(
    parse('"{full_name}" requests verification for the "{iva_type}" IVA'),
    target_fixture="response",
)
def user_requests_verification(full_name: str, iva_type: str, fixtures: JointFixture):
    """Request verification for the IVA"""
    iva = fixtures.state.get_state(f"{iva_type} iva")
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    headers = fixtures.auth.headers(session=session)
    assert iva["id"], "IVA ID not found"
    return fixtures.iva.request_verification(iva["id"], headers=headers)


@when(
    parse('"{full_name}" creates a verification code for the "{iva_type}" IVA'),
    target_fixture="verification_code",
)
def create_iva_verification(full_name: str, iva_type: str, fixtures: JointFixture):
    """Create verification code for the IVA"""
    iva = fixtures.state.get_state(f"{iva_type} iva")
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    headers = fixtures.auth.headers(session=session)
    assert iva["id"], "IVA ID not found"
    return fixtures.iva.create_verification(iva["id"], headers=headers)


@then(
    parse('"{full_name}" sends the verification code to the "{iva_type}" IVA'),
    target_fixture="response",
)
def send_verification_code(
    full_name: str, verification_code: str, iva_type: str, fixtures: JointFixture
):
    """Sends the verification code to the IVA and confirms transmission"""
    iva = fixtures.state.get_state(f"{iva_type} iva")
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    headers = fixtures.auth.headers(session=session)
    assert iva["id"], "IVA ID not found"
    fixtures.state.set_state(f"{iva_type} iva_verification_code", verification_code)
    return fixtures.iva.confirm_transmission(iva["id"], headers=headers)


@when(
    parse('"{full_name}" validates the "{iva_type}" IVA with code'),
    target_fixture="response",
)
def submit_validation_code(full_name: str, iva_type: str, fixtures: JointFixture):
    """Submit the validation code to validate the IVA"""
    iva = fixtures.state.get_state(f"{iva_type} iva")
    verification_code = fixtures.state.get_state(f"{iva_type} iva_verification_code")
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    headers = fixtures.auth.headers(session=session)
    assert iva["id"], "IVA ID not found"
    return fixtures.iva.validate_code(
        verification_code=verification_code, iva_id=iva["id"], headers=headers
    )


@then(parse('the state of IVA is "{state}"'))
def check_iva_state(results: list, state: str, fixtures: JointFixture):
    """Check the state of the IVA"""
    assert isinstance(results, list), f"Expected a list of items, got: {results}"
    iva = results[0]
    assert iva, "No IVA found"
    assert iva["state"].lower() == state.lower(), (
        f"Expected state: {state}, got: {iva['state']}"
    )


@then(parse('"{full_name}" receives an SMS for IVA verification code'))
def check_sms_received(
    full_name: str,
    fixtures: JointFixture,
    timeout: float = 15,
    interval: float = 0.1,
):
    """Check that the user received an SMS for the IVA verification code"""
    slept: float = 0
    found = False
    while slept < timeout and not found:
        since = (now_as_utc() - timedelta(minutes=1)).isoformat()
        lox24_url = (
            fixtures.config.lox24_mock_url.rstrip("/")
            + f"/__admin/requests?url=/sms&method=POST&since={since}"
        )
        response = fixtures.http.get(lox24_url)
        assert response.status_code == 200
        requests = response.json().get("requests", [])
        if len(requests) == 1:
            sms_body = json.loads(requests[0]["request"]["body"])
            found = True
        time.sleep(interval)
        slept += interval

    assert found, f"The verification code SMS was not received by {full_name}."

    assert re.search(EXPECTED_SMS_BODY["text"], sms_body["text"]), (
        f"SMS body does not match expected pattern: {sms_body}"
    )
    for key in (k for k in sms_body.keys() if k != "text"):
        assert sms_body.get(key) == EXPECTED_SMS_BODY[key], (
            f"SMS phone number does not match expected: {sms_body}"
        )
    verification_code = sms_body["text"].split(": ")[1].strip()
    fixtures.state.set_state(
        "Phone iva_verification_code", verification_code
    )  # no need to use dynamic iva_type here, SMS is only sent for Phone IVA
