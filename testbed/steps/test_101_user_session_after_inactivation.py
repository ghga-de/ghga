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

"""Step definition for user session after account inactivation"""

import pytest
from fixtures import PlaywrightFixture
from playwright.sync_api import expect
from pytest_bdd import (  # noqa: RUF100
    given,
    scenarios,
    then,
    when,
)

from .conftest import JointFixture, Response, parse

scenarios("../features/101_user_session_after_inactivation.feature")


@given(parse('the status of "{full_name}" is "{status}"'))
def user_status(full_name: str, status: str, fixtures: JointFixture):
    sub = fixtures.auth.get_sub(full_name)
    saved_status = fixtures.state.get_state(f"status-{sub}")
    assert saved_status, (
        f'Saved status "{saved_status}" does not match with the expected'
    )


@when(parse('"{full_name}" tries to log in to the Data Portal'))
def try_data_portal_login(
    full_name: str, fixtures: JointFixture, playwright: PlaywrightFixture
):
    """Log in through the Data Portal, up to where it loads the session."""
    auth = fixtures.auth
    # the test OIDC provider authorizes the browser as the user who logged in last
    auth.oidc_login(
        name=full_name, email=auth.get_email(full_name), sub=auth.get_sub(full_name)
    )
    playwright.context.clear_cookies()  # start without the session of another user
    page = playwright.page
    page.goto(fixtures.config.data_portal_url)
    page.wait_for_load_state()

    login_button = page.get_by_role("button", name="Log In")
    expect(login_button).to_be_visible(timeout=3000)
    login_button.click()
    ls_login_button = page.get_by_role("menuitem").first
    expect(ls_login_button).to_be_visible(timeout=1000)
    ls_login_button.click()
    page.wait_for_load_state()


@then("the Data Portal shows that the account is disabled")
def data_portal_shows_account_disabled(playwright: PlaywrightFixture):
    """Check the dialog that tells the user the account is disabled."""
    page = playwright.page
    dialog = page.get_by_role("dialog")
    expect(dialog).to_contain_text("Account disabled", timeout=5000)
    expect(dialog).to_contain_text("Your GHGA account has been disabled.")
    dialog.get_by_role("button", name="Close").click()
    expect(dialog).not_to_be_visible()
    # the portal has dropped the session, so the user is logged out
    expect(page.get_by_role("button", name="Log In")).to_be_visible()
