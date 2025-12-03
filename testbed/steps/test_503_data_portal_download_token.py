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

from playwright.sync_api import expect

from .conftest import (
    JointFixture,
    PlaywrightFixture,
    StateStorage,
    given,
    parse,
    scenarios,
    then,
    when,
)

scenarios("../features/503_data_portal_download_token.feature")

TIMEOUT = 3000


@given("no download tokens have been created yet")
def token_state_is_empty(state: StateStorage):
    state.unset_state("download token for")
    state.unset_state("dataset to be downloaded")
    state.unset_state("files to be downloaded")


@given("the files to be downloaded have been announced")
def files_announced_for_download(state: StateStorage):
    assert state.get_state("vcf files in dataset A to be downloaded")
    assert state.get_state("all files in dataset A to be downloaded")
    assert state.get_state("all files in dataset B to be downloaded")


@when("I load the download token creation page")
def create_access_request(fixtures: JointFixture):
    """Open the download token creation page."""
    page = fixtures.playwright.page
    main = page.locator("main")
    url = f"{fixtures.config.data_portal_url}/work-package"
    page.goto(url)
    page.wait_for_load_state()
    expect(main).to_contain_text("Download or upload datasets", ignore_case=True)


@then(parse("I have {num} datasets available to download"))
def check_available_count(fixtures: JointFixture, num: str):
    num_expected = {"no": 0, "one": 1, "two": 2}.get(
        num, int(num) if num.isdigit() else None
    )
    assert num_expected is not None, f"Invalid count: {num}"
    page = fixtures.playwright.page

    # only a select box for available datasets
    select_box = page.locator("mat-form-field")
    expect(select_box).to_have_count(1, timeout=TIMEOUT)
    select_box.first.click()

    options = page.get_by_role(role="option")
    expect(options).to_have_count(num_expected, timeout=TIMEOUT)
    select_box.press("Escape")  # close the select box for next steps


@when(parse('I select the "{dataset_alias}" from available datasets'))
def select_available_dataset(fixtures: JointFixture, dataset_alias: str):
    datasets = fixtures.state.get_state("all available datasets")
    assert dataset_alias in datasets, f"Dataset '{dataset_alias}' not found"
    dataset = datasets[dataset_alias]
    page = fixtures.playwright.page
    main = page.locator("main")

    # only a select box for available datasets
    select_box = page.locator("mat-form-field")
    select_box.first.click()

    options = page.get_by_role(role="option")
    dataset_option = options.get_by_text(dataset["accession"])
    expect(dataset_option).to_have_count(1, timeout=TIMEOUT)
    dataset_option.first.click()
    page.wait_for_load_state()
    expect(main).to_contain_text(dataset["details"]["description"], ignore_case=True)

    # locate again for new form fields appeared after selection
    form_fields = page.locator("mat-form-field")
    expect(form_fields).to_have_count(3, timeout=TIMEOUT)
    expect(form_fields.nth(1)).to_contain_text("File IDs", ignore_case=True)
    expect(form_fields.nth(2)).to_contain_text("Crypt4GH key", ignore_case=True)


@when(
    parse(
        'I create a download token for "{file_scope}" files in dataset "{dataset_alias}"'
    )
)
def create_download_token(fixtures: JointFixture, file_scope: str, dataset_alias: str):
    datasets = fixtures.state.get_state("all available datasets")
    assert dataset_alias in datasets, f"Dataset '{dataset_alias}' not found"
    dataset_char = dataset_alias.replace("DS_", "")
    page = fixtures.playwright.page
    main = page.locator("main")
    form_fields = page.locator("mat-form-field")

    file_ids = None
    if file_scope in ["vcf", "fastq"]:
        all_dataset_files = fixtures.state.get_state(
            f"{file_scope} files in dataset {dataset_char} to be downloaded"
        )
        extension = f".{file_scope}.gz"
        file_ids = [
            file["id"] for file in all_dataset_files if file["extension"] == extension
        ]
    elif file_scope != "all":
        raise ValueError(f"Unknown file_scope '{file_scope}'")

    # fill file IDs
    if file_ids is not None:
        file_ids_field = form_fields.nth(1).locator("textarea")
        file_ids_field.fill(",".join(file_ids))

    # fill public key
    crypt4gh_field = form_fields.nth(2).locator("input")
    crypt4gh_field.fill(fixtures.config.user_public_crypt4gh_key)

    submit_button = main.get_by_role(
        role="button", name="Generate an access token for download"
    )
    expect(submit_button).to_be_enabled(timeout=TIMEOUT)
    submit_button.click()
    page.wait_for_load_state()

    expect(main).to_contain_text(
        "Your download token has been created", ignore_case=True
    )
    download_token = page.locator("mat-card").locator("pre").inner_text()
    id_, token = download_token.split(":")
    assert 20 <= len(id_) < 40 and 80 < len(token) < 120
    fixtures.state.set_state(
        f"download token for {file_scope} files in dataset {dataset_char}",
        download_token,
    )
