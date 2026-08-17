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

"""Shared test used for steps with prefix test_4*"""

import re

from fixtures import (
    Config,
    JointFixture,
    MongoFixture,
    PlaywrightFixture,
    StateStorage,
)
from playwright.sync_api import expect
from pytest_bdd import given, then, when

from steps.utils import ADMIN_PAGES, parse


@given(
    parse('I am logged in to the Data Portal as "{full_name}"'),
    target_fixture="active_user",
)
def login_to_data_portal(
    full_name: str,
    fixtures: JointFixture,
) -> str:
    """Login to the Data Portal."""
    fixtures.playwright.login(
        full_name, config=fixtures.config, auth_fixture=fixtures.auth
    )
    return full_name


@given("the user has logged out of the Data Portal")
def logout_from_data_portal(fixtures: JointFixture) -> None:
    """Ensure the current user is logged out of the Data Portal."""
    fixtures.playwright.logout(config=fixtures.config)


@given("I load the homepage")
def go_to_main_page(fixtures, playwright: PlaywrightFixture):
    """Load to the homepage."""
    playwright.page.goto(fixtures.config.data_portal_url)
    playwright.page.wait_for_load_state()


@when("I navigate to the dataset browsing page")
def open_browse_page(playwright: PlaywrightFixture):
    """Navigate to the dataset browsing page."""
    button = playwright.page.get_by_text("Browse Data").first
    expect(button).to_be_visible()
    button.click()
    expect(playwright.page).to_have_url(re.compile(r"/browse$"))


@then("the homepage content is displayed")
def check_homepage_content(playwright: PlaywrightFixture):
    """Check the static homepage content."""
    expect(playwright.page).to_have_title("Home | GHGA Data Portal")
    heading = playwright.page.get_by_role("heading")
    expect(heading.nth(0)).to_contain_text("The German Human Genome‑Phenome Archive")  # noqa: RUF001
    expect(heading.nth(0)).to_contain_text("Data Portal")
    expect(heading.nth(1)).to_contain_text("Statistics")  # Second section header
    expect(heading.nth(2)).to_contain_text("About GHGA")  # Third section header


@then("all the available datasets are displayed")
def check_example_datasets(fixtures: JointFixture, playwright: PlaywrightFixture):
    """Check the example datasets on page."""
    expect(playwright.page).to_have_url(re.compile(r"/browse$"))
    all_datasets = fixtures.state.get_state("all available datasets")

    main = playwright.page.locator("main")
    expect(main).to_contain_text(f"Total Datasets:{len(all_datasets)}")

    search_results = playwright.page.locator("app-search-result")
    expect(search_results).to_have_count(len(all_datasets))

    for dataset in all_datasets.values():
        expect(main).to_contain_text(dataset["title"])

    # inner content should not be visible yet
    expect(main).not_to_contain_text("An interesting dataset A of complete example set")
    expect(main).not_to_contain_text("7 Files")


@when(parse('I select the "{dataset_name}" dataset'))
def click_on_dataset(
    dataset_name: str, fixtures: JointFixture, playwright: PlaywrightFixture
):
    """Click on a dataset to expand its summary."""
    expect(playwright.page).to_have_url(re.compile(r"/browse$"))
    all_datasets = fixtures.state.get_state("all available datasets")
    dataset = all_datasets[dataset_name]
    accordion_list = playwright.page.locator(".mat-accordion")
    dataset_button = accordion_list.get_by_text(dataset["title"])
    dataset_button.click()
    playwright.page.wait_for_load_state()


@when(parse('I open the details of "{alias}" dataset'))
def open_dataset_details(fixtures: JointFixture, alias: str):
    """Expand the table for details of the dataset."""
    datasets = fixtures.state.get_state("all available datasets")
    accession = datasets[alias]["accession"]
    page = fixtures.playwright.page
    expect(page.locator("main")).to_contain_text(
        f"An interesting dataset {alias.split('_')[1]} of complete example set"
    )
    # Other dataset buttons exist but hidden, still caught by selectors
    button = page.get_by_text("Dataset Details").locator("visible=true").first
    button.click()
    page.wait_for_load_state()
    expect(page).to_have_url(re.compile(f".*/dataset/{accession}"))


@when(parse('I load the admin page "{admin_page}"'))
def open_admin_page(fixtures: JointFixture, admin_page: str):
    """Open a specific admin page."""
    assert admin_page in ADMIN_PAGES, f"Unknown admin page: {admin_page}"
    page_path = ADMIN_PAGES[admin_page][0]
    url = f"{fixtures.config.data_portal_url.rstrip('/')}/{page_path}"
    page = fixtures.playwright.page
    page.goto(url)
    page.wait_for_load_state()
    main = page.locator("main")
    expect(main).to_contain_text(ADMIN_PAGES[admin_page][1])


@when("I navigate to the user account page")
def open_account_page(fixtures: JointFixture):
    """Open the user account page from the homepage."""
    page = fixtures.playwright.page
    profile_button = page.get_by_role("button", name="Account")
    expect(profile_button).to_be_visible()
    profile_button.click()
    profile_menu_items = page.get_by_role("menuitem")
    expect(profile_menu_items.nth(0)).to_contain_text("Your GHGA account page")
    profile_menu_items.nth(0).click()
    page.wait_for_load_state()


@given("we have no accession mappings yet")
def empty_file_mappings(config: Config, mongo: MongoFixture):
    """Unmap the RS accession records so the box can be (re-)mapped via the UI."""
    mappings = mongo.find_documents(
        config.rs_db_name, config.rs_mappings_collection, sloppy=True
    )
    for document in mappings:
        document["file_id"] = None
        document["mapped"] = None
        mongo.upsert_document(
            config.rs_db_name,
            config.rs_mappings_collection,
            document,
            extend_mapping=False,
        )


@given("we have no upload boxes yet")
def clear_upload_boxes(state: StateStorage, config: Config, mongo: MongoFixture):
    """Clear any existing upload boxes from the state."""
    state.unset_state("rdub_primary")
    state.unset_state("rdub_secondary")
    collections = [
        (config.ucs_db_name, config.ucs_fub_collection),
        (config.rs_db_name, config.rs_rdub_collection),
        (config.wps_db_name, config.wps_rdub_collection),
    ]
    for db_name, collection_name in collections:
        mongo.empty_databases(db_name, collection_name)
