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
import time

from playwright.sync_api import expect

from .conftest import (
    JointFixture,
    parse,
    scenarios,
    then,
    when,
)
from .utils import IVA_TYPE_NAMES

scenarios("../features/503_data_portal_access_grants.feature")

TIMEOUT = 3000

UI_APP_CONTEXT = {
    "access requests": {
        "list_component": "app-access-request-manager-list",
        "no_data_text": "No access requests found. Try removing some filter conditions.",
        "form_component": "app-access-request-manager-filter",
        "expected_num_of_filters": 10,
        "dataset_filter": "mat-form-field:has-text('Dataset title or ID')",
    },
    "access grants": {
        "list_component": "app-access-grant-manager-list",
        "no_data_text": "No access grants found. Try removing some filter conditions.",
        "form_component": "app-access-grant-manager-filter",
        "expected_num_of_filters": 3,
        "dataset_filter": "mat-form-field:has-text('Dataset ID')",
    },
}


@when(parse('I request access to the "{alias}" dataset'))
def create_access_request(fixtures: JointFixture, alias: str):
    """Create an access request for the given dataset alias."""
    datasets = fixtures.state.get_state("all available datasets")
    page = fixtures.playwright.page
    assert alias in datasets, f"Dataset '{alias}' not found"
    accession = datasets[alias]["accession"]

    # User can create an access request without navigating to the details page
    if "/dataset/" in page.url:
        expect(page).to_have_url(re.compile(f".*/dataset/{accession}"))
    # The same button is available on both pages
    request_button = page.get_by_role("button", name="Request Access")
    request_button.click()

    dialog = page.locator("app-access-request-dialog")
    expect(dialog).to_contain_text("Request access for dataset", timeout=TIMEOUT)
    form_field = dialog.locator("mat-form-field:has-text('Details about your request')")
    form_field.locator("textarea").fill(f"Access request for {alias}")
    submit_button = page.get_by_role("button", name="Submit")
    submit_button.click()
    time.sleep(2)  # wait for API call to complete, couldn't find a better way


@then(parse('the table shows {num} "{status}" item for "{full_name}"'))
@then(parse('the table shows {num} "{status}" items for "{full_name}"'))
def check_admin_table(fixtures: JointFixture, num: str, status: str, full_name: str):
    """Check the admin table shows the expected number of items for the given user."""
    page = fixtures.playwright.page
    num_expected = {"no": 0, "one": 1, "two": 2}.get(
        num, int(num) if num.isdigit() else None
    )
    assert num_expected is not None, f"Invalid count: {num}"

    _, name = fixtures.auth.split_title(full_name)
    table = page.locator("table")
    expect(table).to_be_visible()
    if num_expected == 0:
        expect(table).to_contain_text(
            re.compile(r"No .* found\. Try removing some filter conditions\.")
        )
    else:
        assert name, "Name must be provided if num_expected > 0"
        rows = table.locator("tbody tr", has_text=name).filter(
            has_text=re.compile(status, re.IGNORECASE)
        )
        expect(rows).to_have_count(num_expected)


@when(parse('I filter "{app}" for dataset "{alias}"'))
def filter_admin_table_by_dataset(fixtures: JointFixture, app: str, alias: str):
    """Filter the given app by the dataset accession of the given alias."""
    app = app.lower()
    assert app in UI_APP_CONTEXT, f"Unknown app name: {app}"
    page = fixtures.playwright.page
    all_datasets = fixtures.state.get_state("dataset_accessions")
    dataset_accession = all_datasets[alias]["dataset_accession"]

    form_selector = UI_APP_CONTEXT[app]["form_component"]
    form = page.locator(form_selector)
    expect(form.locator("mat-form-field")).to_have_count(
        UI_APP_CONTEXT[app]["expected_num_of_filters"], timeout=TIMEOUT
    )
    form.locator(UI_APP_CONTEXT[app]["dataset_filter"]).locator("input").fill(
        dataset_accession
    )


@when("I filter access requests by all statuses")
def filter_access_requests_all_statuses(fixtures: JointFixture):
    """Filter access requests by all statuses."""
    page = fixtures.playwright.page
    form_selector = "app-access-request-manager-filter"
    form = page.locator(form_selector)
    expect(form.locator("mat-form-field")).to_have_count(10, timeout=TIMEOUT)

    form.locator("mat-form-field:has-text('Resolution')").click()
    page.get_by_role(
        "option", name=re.compile("All resolutions", re.IGNORECASE)
    ).first.click()


@when("I select the filtered item")
def open_filtered_item(fixtures: JointFixture):
    """Click and open the details of the only item in the filtered table."""
    page = fixtures.playwright.page
    table = page.locator("table")
    expect(table).to_be_visible()
    rows = table.locator("tbody tr")
    expect(rows).to_have_count(1, timeout=TIMEOUT)  # Check there is only one item
    rows.first.click()
    page.wait_for_load_state()


@then(parse('I get the access request details on dataset "{alias}" for "{full_name}"'))
def check_access_request_detail_page(
    fixtures: JointFixture, alias: str, full_name: str
):
    """Check the access request detail page shows correct information."""
    page = fixtures.playwright.page
    all_datasets = fixtures.state.get_state("all available datasets")
    dataset = all_datasets[alias]
    dataset_accession = dataset["accession"]

    main = page.locator("main")

    expect(main).to_contain_text("Request & Dataset")
    expect(main).to_contain_text(f"Dataset ID:{dataset_accession}")

    expect(main).to_contain_text("DAC & Requester")
    expect(main).to_contain_text(f"Requester:{full_name}")
    dac = dataset["details"]["data_access_policy"]["data_access_committee"]
    expect(main).to_contain_text(f"DAC:{dac['alias']} - {dac['email']}")

    expect(main).to_contain_text("Verification Address")
    user_iva = fixtures.state.get_state("Phone iva")
    expect(main).to_contain_text(
        f"{IVA_TYPE_NAMES[user_iva['type']]}: {user_iva['value']} Verified"
    )

    expect(main).to_contain_text("Access Timeline & Details")
    expect(main).to_contain_text("Notes")


@then(parse('the status of the access request is "{status}"'))
def check_access_request_status(fixtures: JointFixture, status: str):
    """Check the status of the access request on the detail page."""
    page = fixtures.playwright.page
    expect(page.locator("main")).to_contain_text(f"Resolution:{status.lower()}")


@when(parse('I "{action}" the access request'))
def deny_access_requests(fixtures: JointFixture, action: str):
    """Deny or allow the access request based on the action parameter."""
    page = fixtures.playwright.page

    assert "/access-request-manager/" in page.url, (
        f"Not on access request detail page. Current URL:{page.url}"
    )

    assert action in ("allow", "deny"), f"Unknown action: {action}"
    button_name = action.capitalize()
    action_button = page.get_by_role("button", name=button_name)
    action_button.click()

    confirm_dialog = page.locator("app-confirm-dialog")
    if action == "allow":
        expect(confirm_dialog).to_contain_text("Confirm approval of the access request")
        confirm_button = page.get_by_role("button", name="Confirm allowance")
    elif action == "deny":
        expect(confirm_dialog).to_contain_text("Confirm denial of the access request")
        confirm_button = page.get_by_role("button", name="Confirm denial")
    else:
        raise ValueError(f"Unknown action: {action}")

    confirm_button.click()
    time.sleep(2)  # wait for API call to complete, couldn't find a better way
