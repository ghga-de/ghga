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

"""Fixtures for Playwright testing."""

import time

from playwright.sync_api import expect, sync_playwright
from pytest import fixture

from fixtures.state import StateStorage

__all__ = ["PlaywrightFixture", "playwright_fixture"]

_INSECURE_AS_SECURE = "http://op.test,http://data-portal,"


class PlaywrightFixture:
    """Fixture for managing Playwright resources."""

    def __init__(self, playwright_instance, state):
        self.playwright_instance = playwright_instance
        # We use only Chromium because Archive Test Bed tests service integration.
        # Browser compatibility is not tested here.
        self.browser = playwright_instance.chromium.launch(
            headless=True,  # Set to False for browser GUI during test runs
        )
        self.context = self.browser.new_context(
            ignore_https_errors=True,
        )
        self.page = self.context.new_page()
        self.page.on("console", lambda msg: print(msg.text))
        self.state = state

    def login(self, full_name, config, auth_fixture):
        sub = auth_fixture.get_sub(full_name)

        # Check last logged in user
        # UI requires to be logged via OIDC first
        logged_in_as = self.state.get_state("logged in as")
        assert logged_in_as == sub, "Logged in as {logged_in_as}. Expected {full_name}"
        if "steward" in logged_in_as:
            print("Steward user")

        # Check user has a TOTP token for 2FA authentication
        token = self.state.get_state(f"totp-token-{sub}")
        assert token, f"No TOTP token found for {full_name}"

        main = self.page.locator("main")
        self.page.goto(config.data_portal_url)
        self.page.wait_for_load_state()

        login_button = self.page.get_by_role("button", name="Log In")
        expect(login_button).to_be_visible(timeout=3000)
        login_button.click()

        ls_login_button = self.page.get_by_role(role="menuitem").first
        expect(ls_login_button).to_be_visible(timeout=1000)
        assert ls_login_button.locator("img").get_attribute("alt") == "LS Login"
        ls_login_button.click()
        self.page.wait_for_load_state()

        expect(main).to_contain_text("Two-factor authentication")
        totp_input_box = self.page.get_by_label("Authentication code").first
        expect(totp_input_box).to_be_visible()

        totp = auth_fixture.generate_totp(token)
        # TOTP input box auto-submits when the correct code is entered
        with self.page.expect_response(
            lambda response: "/verify-totp" in response.url
        ) as response_info:
            totp_input_box.fill(totp)

        response = response_info.value
        if response.status != 204:
            raise AssertionError(
                f"TOTP verification failed with status {response.status}"
            )

        self.page.wait_for_load_state()

        login_button = self.page.get_by_role("button", name="Log In")
        expect(login_button).not_to_be_visible()

        login_button = self.page.get_by_role("button", name="Account")
        expect(login_button).to_be_visible()

    def logout(self, config):
        # UI requires to be logged via OIDC first
        logged_in_as = self.state.get_state("logged in as")
        assert logged_in_as

        self.page.goto(config.data_portal_url)
        self.page.wait_for_load_state()

        profile_button = self.page.get_by_role("button", name="Account")
        try:
            # In case of delay on button appearing, give some time to be visible
            expect(profile_button).to_be_visible(timeout=3000)
            # Assume user is logged out only after timeout
        except AssertionError:
            return
        profile_button.click()

        profile_menu_items = self.page.get_by_role(role="menuitem")
        logout_button = profile_menu_items.nth(2)
        expect(profile_menu_items.nth(2)).to_be_visible()
        assert "log out" in logout_button.text_content().lower()
        logout_button.click()
        self.page.wait_for_load_state()

        login_button = self.page.get_by_role("button", name="Log In")
        expect(login_button).to_be_visible()

    def teardown(self):
        self.page.close()
        self.context.close()


@fixture(name="playwright", scope="session")
def playwright_fixture(state: StateStorage):
    """Fixture to provide a Playwright browser instance."""
    with sync_playwright() as p:
        fixture = PlaywrightFixture(playwright_instance=p, state=state)
        yield fixture
        fixture.teardown()
