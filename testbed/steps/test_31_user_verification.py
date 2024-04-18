# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

from fixtures.iva import IVA

from .conftest import (
    JointFixture,
    Response,
    given,
    parse,
    scenarios,
    then,
    when,
)

scenarios("../features/31_user_verification.feature")


# Types are case-sensitive as they are requested by the API
USER_IVAS = {
    "Phone": "01234567890",
    "Fax": "09876543210",
    "PostalAddress": "1234 Main Str.",
    "InPerson": "A person",
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


@when(parse('"{full_name}" adds "{prop}" as an IVA'), target_fixture="iva")
def user_adds_an_iva(full_name: str, prop: str, fixtures: JointFixture) -> IVA:
    """Add an IVA to the user account"""
    iva_value = USER_IVAS.get(prop)
    assert iva_value, f"Incompatible IVA: {prop}. Available types: {USER_IVAS.keys()}]"
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    assert session, "User session not found"
    assert session.user_id, "User ID not found"
    headers = fixtures.auth.headers(session=session)
    iva = fixtures.iva.create(
        iva_type=prop, iva_value=iva_value, user_id=session.user_id, headers=headers
    )
    fixtures.state.set_state("iva", iva.model_dump())
    return iva


@when(parse('"{full_name}" retrieves the list of IVAs'), target_fixture="results")
def list_user_ivas(full_name: str, fixtures: JointFixture):
    """Retrieve the list of IVAs for the user"""
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    assert session, "User session not found"
    assert session.user_id, "User ID not found"
    headers = fixtures.auth.headers(session=session)
    return fixtures.iva.retrieve(session.user_id, headers)


@when(
    parse('"{full_name}" requests verification for the IVA'), target_fixture="response"
)
def user_requests_verification(full_name: str, fixtures: JointFixture):
    """Request verification for the IVA"""
    iva = fixtures.state.get_state("iva")
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    headers = fixtures.auth.headers(session=session)
    assert iva["id"], "IVA ID not found"
    return fixtures.iva.request_verification(iva["id"], headers=headers)


@when(
    parse('"{full_name}" creates a verification code for the IVA'),
    target_fixture="verification_code",
)
def create_iva_verification(full_name: str, fixtures: JointFixture):
    """Create verification code for the IVA"""
    iva = fixtures.state.get_state("iva")
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    headers = fixtures.auth.headers(session=session)
    assert iva["id"], "IVA ID not found"
    return fixtures.iva.create_verification(iva["id"], headers=headers)


@then(parse('"{full_name}" sends the verification code to the IVA'))
def send_verification_code(verification_code: str, fixtures: JointFixture):
    """Send the verification code to the IVA

    The Data Steward sends the code to the IVA. Here we only store it.
    """
    # TODO: Send and check the verification code is received by the IVA
    fixtures.state.set_state("iva_verification_code", verification_code)


@then(
    parse('"{full_name}" confirms the transmission of verification code'),
    target_fixture="response",
)
def confirm_transmission(full_name: str, fixtures: JointFixture):
    """Confirm the transmission of the verification code to the IVA"""
    iva = fixtures.state.get_state("iva")
    session = fixtures.auth.get_saved_session(
        name=full_name, state_store=fixtures.state
    )
    headers = fixtures.auth.headers(session=session)
    assert iva["id"], "IVA ID not found"
    return fixtures.iva.confirm_transmission(iva["id"], headers=headers)


@when(
    parse('"{full_name}" validates the IVA with code'),
    target_fixture="response",
)
def submit_validation_code(full_name: str, fixtures: JointFixture):
    """Submit the validation code to validate the IVA"""
    iva = fixtures.state.get_state("iva")
    verification_code = fixtures.state.get_state("iva_verification_code")
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
    assert (
        iva["state"].lower() == state.lower()
    ), f"Expected state: {state}, got: {iva['state']}"
