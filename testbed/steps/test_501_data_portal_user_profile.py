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

"""Step definitions for testing the data portal UI."""

import re

from playwright.sync_api import expect

from .conftest import (
    JointFixture,
    PlaywrightFixture,
    given,
    parse,
    scenarios,
    then,
    when,
)
from .utils import IVA_TYPE_NAMES, UI_TIMEOUT, USER_PHONE_NUMBERS

scenarios("../features/501_data_portal_user_profile.feature")

STATE_MSG_MAP = {
    "verified": "Address has been verified",
    "unverified": "Needs verification",
    "coderequested": "Waiting for verification",
    "codetransmitted": "Code has been sent",
}


@given("all users have only a verified IVA")
def delete_ivas(fixtures: JointFixture):
    """Removes all IVA documents except with a "Verified" state.

    Ensures that only a single verified IVA remains per user. It's
    the initial state for Data portal tests.
    """
    user_iva = fixtures.state.get_state("Phone iva")
    # The IVA DS account and John Doe have the same IVA value
    query = {"value": {"$ne": user_iva["value"]}}
    fixtures.mongo.remove_documents(
        fixtures.config.ums_db_name, fixtures.config.ums_user_ivas_collection, query
    )


@then(parse('I get the homepage interface for "{full_name}"'))
def check_homepage_for_user(full_name: str, fixtures: JointFixture):
    """Check that the homepage interface is as expected for the user role."""
    page = fixtures.playwright.page
    heading = page.get_by_role("heading")
    expected_header = "The German Human Genome‑Phenome Archive"  # noqa: RUF001
    expect(heading.first).to_contain_text(expected_header)

    # Validate profile button and logged in user initials
    profile_button = page.get_by_role("button", name="Account")
    expect(profile_button).to_be_visible()
    assert profile_button.inner_text() == fixtures.auth.get_initials(full_name)

    # Validate navigation items
    expected_navigation_items = ["Browse Data", "Docs", "FAQ", "Home", "System Status"]
    if full_name == "Data Steward":
        expected_navigation_items.append("Admin")
    navigation = page.locator("mat-nav-list").nth(0).inner_text()
    assert sorted(
        navigation.replace("open_in_new\n", "")
        .replace("arrow_drop_down\n", "")
        .split("\n")
    ) == sorted(expected_navigation_items)

    # Validate profile menu items
    profile_button.click()
    profile_menu_items = page.get_by_role("menuitem")
    expect(profile_menu_items.nth(0)).to_contain_text("Your GHGA account page")
    expect(profile_menu_items.nth(1)).to_contain_text("Manage LS Login account")
    expect(profile_menu_items.nth(2)).to_contain_text("Log out")


@then(parse('I get the user profile page of "{full_name}"'))
def validate_profile_page(fixtures: JointFixture, full_name: str):
    """Validate the user profile page."""
    page = fixtures.playwright.page

    def inner_text_as_list(component):
        return component.inner_text().replace("\n\n", "\n").split("\n")

    email = fixtures.auth.get_email(full_name)
    main = page.locator("main")
    expect(main).to_contain_text("User Account")
    expect(main).to_contain_text(full_name)

    profile_components = page.locator("mat-card")
    expect(profile_components).to_have_count(5)

    email_inner_texts = inner_text_as_list(profile_components.nth(0))
    assert email_inner_texts[0] == "Email"
    assert (
        email_inner_texts[2]
        == f"We will communicate with you via this email address: {email}"
    )

    expect(profile_components.nth(1)).to_contain_text(
        "Independent Verification Addresses (IVAs)"
    )
    expect(profile_components.nth(2)).to_contain_text("Dataset Access")
    expect(profile_components.nth(3)).to_contain_text("Pending Access Requests")
    return full_name


def _iva_rows(page, text: str):
    """Get the rows of the IVA list in the user profile page holding the text."""
    return page.locator("app-user-iva-list > .grid > .grid").filter(has_text=text)


@then(parse('I have a "{iva_type}" contact address with state "{iva_state}"'))
@then(parse('I have an "{iva_type}" contact address with state "{iva_state}"'))
def check_ivas_in_profile(fixtures: JointFixture, iva_type: str, iva_state: str):
    """Check the IVAs in the user profile page."""
    page = fixtures.playwright.page
    state_msg = STATE_MSG_MAP[iva_state.lower()]
    # IVA list is <div grid> elements without specific identifiers to select.
    iva_selector = f'app-user-iva-list > .grid > .grid:has-text("{state_msg}")'
    iva = page.locator(iva_selector)
    expect(iva).to_contain_text(iva_type)  # Confirm type


@then(parse('I have "{num}" granted access requests'))
def check_granted_access(fixtures: JointFixture, num: str, active_user: str):
    """Check the datasets with granted access in the user account page."""
    page = fixtures.playwright.page
    try:
        num_expected = {"no": 0, "one": 1, "two": 2}[num]
    except KeyError:
        num_expected = int(num)

    component = page.locator("app-granted-access-grants-list")

    if num_expected == 0:
        # Expect no datasets on UI
        assert (
            component.locator("p").inner_text()
            == "You do not yet have access to any datasets."
        )
    else:
        # Retrieve known datasets for user from state store to compare
        session = fixtures.auth.get_saved_session(
            name=active_user, state_store=fixtures.state
        )
        assert session, "User session not found"
        user_datasets = fixtures.state.get_state("datasets users can access")
        datasets_on_ui = component.locator("a")
        expect(datasets_on_ui).to_have_count(num_expected, timeout=UI_TIMEOUT)
        ui_texts = datasets_on_ui.all_inner_texts()
        for dataset_id in user_datasets.values():
            assert any(dataset_id in text for text in ui_texts), (
                f"Dataset ID {dataset_id} not found in UI items: {ui_texts}"
            )

        expect(
            component.get_by_role("button").get_by_text("Create Token")
        ).to_have_count(2, timeout=UI_TIMEOUT)


@then("I have no pending access requests")
def check_pending_requests_in_profile(playwright: PlaywrightFixture):
    """Check that there are no pending access requests in the user profile page."""
    requests_component = playwright.page.locator("mat-card").nth(3)
    assert (
        requests_component.locator("p").inner_text()
        == "You do not yet have pending access requests."
    )


@when(parse('I add a new "{iva_type}" contact address with value "{iva_value}"'))
def add_new_iva(playwright: PlaywrightFixture, iva_type: str, iva_value: str):
    """Add a new IVA in the user profile page."""
    if iva_type not in ["SMS", "In Person"]:
        raise ValueError(f"Unsupported IVA type: {iva_type}")
    page = playwright.page

    iva_add_button = page.get_by_role("button", name="Add an IVA")
    expect(iva_add_button).to_be_visible(timeout=UI_TIMEOUT)
    iva_add_button.click()

    iva_dialog = page.locator("app-new-iva-dialog").first
    expect(iva_dialog).to_contain_text(
        "Please select one of the following IVA types", timeout=UI_TIMEOUT
    )

    radio_group = iva_dialog.locator("mat-button-toggle-group")
    expect(radio_group).to_be_visible(timeout=UI_TIMEOUT)
    iva_options = iva_dialog.get_by_role("radio").all_inner_texts()
    assert sorted(iva_options) == sorted(["SMS", "In Person"]), (
        f"IVA type options mismatch: {iva_options}"
    )

    type_button = iva_dialog.get_by_role(
        "radio", name=re.compile(re.escape(iva_type), re.IGNORECASE)
    )
    expect(type_button.first).to_be_visible(timeout=UI_TIMEOUT)
    type_button.first.click()

    input_box = iva_dialog.locator("input").first
    expect(input_box).to_be_visible(timeout=UI_TIMEOUT)
    input_box.fill(iva_value)

    submit_button = iva_dialog.get_by_role("button", name="Submit").first
    expect(submit_button).to_be_visible(timeout=UI_TIMEOUT)
    submit_button.click()
    page.wait_for_load_state()


@when(parse('I request verification for the "{iva_type}" IVA'))
def request_iva_verification(playwright: PlaywrightFixture, iva_type: str):
    """Request verification of the one unverified IVA of the given type.

    Sending an SMS needs the user's consent, so for an SMS address this leaves
    the consent dialog open for the steps that check and answer it.
    """
    page = playwright.page
    page.wait_for_selector(
        "app-user-iva-list > .grid", timeout=UI_TIMEOUT
    )  # Wait for items to be loaded
    unverified_items = _iva_rows(page, iva_type).filter(
        has_text=STATE_MSG_MAP["unverified"]
    )
    expect(unverified_items).to_have_count(1, timeout=UI_TIMEOUT)
    request_button = unverified_items.get_by_role("button", name="Request verification")
    expect(request_button).to_be_visible()
    request_button.click()

    page.wait_for_selector("app-confirm-dialog", timeout=UI_TIMEOUT)
    if iva_type == "SMS":
        return
    confirm_dialog = page.locator("app-confirm-dialog").first
    expect(confirm_dialog).to_contain_text("Request verification of your address")
    continue_button = page.get_by_role(
        "button", name=re.compile(r"Continue", re.IGNORECASE)
    )
    expect(continue_button).to_be_visible()
    continue_button.click()
    page.wait_for_load_state()


@then("I list all the known IVAs in the system")
def check_all_ivas_on_portal(fixtures: JointFixture, active_user):
    page = fixtures.playwright.page
    session = fixtures.auth.get_saved_session(
        name=active_user, state_store=fixtures.state
    )
    assert session, "User session not found"
    assert session.user_id, "User ID not found"
    headers = fixtures.auth.headers(session=session)
    results = fixtures.iva.list_all(headers)
    item_selector = "app-iva-manager-list tbody tr"
    page.wait_for_selector(item_selector, timeout=UI_TIMEOUT)
    ui_rows = page.locator(item_selector).all_text_contents()
    assert len(results) == len(ui_rows), "IVA count mismatch"
    for iva in results:
        user_name = iva.get("user-name", "")
        iva_type = iva.get("type", "")
        iva_type = IVA_TYPE_NAMES.get(iva_type, iva_type)
        iva_value = iva.get("value", "")
        found = any(  # unordered front end data should include the IVA
            user_name in row and iva_type in row and iva_value in row for row in ui_rows
        )
        if not found:
            raise AssertionError(f"IVA not found in UI: {iva}")


@when("I send the code to the IVA waiting for verification")
def create_code_for_iva(fixtures: JointFixture, active_user):
    page = fixtures.playwright.page
    create_code_button = page.get_by_role("button", name="Create code")
    assert create_code_button.count() == 1, (
        f"Expecting one create code button, found {create_code_button.count()}"
    )
    create_code_button.click()
    dialog_selector = "app-code-creation-dialog"
    dialog = page.locator(dialog_selector)
    expect(dialog).to_contain_text("Verification code created", timeout=UI_TIMEOUT)
    code = dialog.locator("table input").input_value()
    fixtures.state.set_state("iva_verification_code", code)
    confirm_button = dialog.get_by_role("button", name="Confirm transmission").first
    expect(confirm_button).to_be_visible(timeout=UI_TIMEOUT)
    confirm_button.click()
    page.wait_for_load_state()


@then(parse('I filter {num} IVAs with state "{iva_state}"'))
@then(parse('I filter {num} IVA with state "{iva_state}"'))
def filter_ivas_as_admin(fixtures: JointFixture, num: str, iva_state: str):
    try:
        num_expected = int(num)
    except ValueError:
        num_expected = {"no": 0, "one": 1, "two": 2}[num]

    page = fixtures.playwright.page
    form_selector = "app-iva-manager-filter"
    form = page.locator(form_selector)
    expect(form.locator("mat-form-field")).to_have_count(4, timeout=UI_TIMEOUT)

    form.locator("mat-form-field:has-text('All status values')").click()
    page.get_by_role("option", name=re.compile(iva_state, re.IGNORECASE)).first.click()

    rows = page.locator("app-iva-manager-list tbody tr")
    expect(rows).to_have_count(num_expected, timeout=UI_TIMEOUT)
    if num_expected:
        assert iva_state in rows.first.inner_text()


def _sms_address(which: str) -> str:
    """Get the SMS address of the user profile page with the given number."""
    return f"SMS: {USER_PHONE_NUMBERS[which]}"


@when(parse('I add a new "SMS" contact address with the "{which}" number'))
def add_new_sms_iva(playwright: PlaywrightFixture, which: str):
    """Add an SMS address with the main or the other number of the suite."""
    add_new_iva(playwright, "SMS", USER_PHONE_NUMBERS[which])


@then(parse('the "{which}" SMS contact address has state "{iva_state}"'))
def check_sms_iva_state_in_profile(
    playwright: PlaywrightFixture, which: str, iva_state: str
):
    """Check the state of the SMS address with the given number."""
    row = _iva_rows(playwright.page, _sms_address(which))
    expect(row).to_have_count(1, timeout=UI_TIMEOUT)
    expect(row).to_contain_text(STATE_MSG_MAP[iva_state.lower()], timeout=UI_TIMEOUT)


@then(parse('I am asked for consent to send an SMS to the "{which}" number'))
def check_sms_consent_dialog(playwright: PlaywrightFixture, which: str):
    """Check the consent dialog the portal shows before sending a verification SMS."""
    number = USER_PHONE_NUMBERS[which]
    dialog = playwright.page.locator("app-confirm-dialog").first
    expect(dialog).to_be_visible(timeout=UI_TIMEOUT)
    expect(dialog.get_by_role("heading")).to_have_text("Send verification code by SMS")
    expect(dialog).to_contain_text(
        f"We will send a verification code by SMS to your phone number {number}."
    )
    expect(dialog).to_contain_text(
        'By clicking "Send SMS", you agree to receive this message.'
    )
    expect(dialog.get_by_role("button", name="Cancel", exact=True)).to_be_visible()
    expect(dialog.get_by_role("button", name="Send SMS", exact=True)).to_be_visible()


@when("I consent to sending the SMS")
def consent_to_sms(playwright: PlaywrightFixture):
    """Confirm the consent dialog, which sends the verification SMS."""
    dialog = playwright.page.locator("app-confirm-dialog").first
    dialog.get_by_role("button", name="Send SMS", exact=True).click()
    expect(dialog).to_have_count(0, timeout=UI_TIMEOUT)


@when(parse('I delete the "{which}" SMS contact address'))
def delete_sms_iva_in_profile(playwright: PlaywrightFixture, which: str):
    """Delete the SMS address with the given number through the user profile page."""
    page = playwright.page
    address = _sms_address(which)
    row = _iva_rows(page, address)
    expect(row).to_have_count(1, timeout=UI_TIMEOUT)
    row.get_by_role("button", name="Delete").click()
    dialog = page.locator("app-confirm-dialog").first
    expect(dialog.get_by_role("heading")).to_have_text(
        "Confirm deletion of IVA", timeout=UI_TIMEOUT
    )
    expect(dialog).to_contain_text(f"Please confirm deleting the {address}.")
    dialog.get_by_role("button", name="Confirm deletion", exact=True).click()
    expect(dialog).to_have_count(0, timeout=UI_TIMEOUT)


@then(parse('the "{which}" SMS contact address is gone'))
def check_sms_iva_gone(playwright: PlaywrightFixture, which: str):
    """Check that the SMS address with the given number is not listed any more."""
    rows = _iva_rows(playwright.page, _sms_address(which))
    expect(rows).to_have_count(0, timeout=UI_TIMEOUT)
