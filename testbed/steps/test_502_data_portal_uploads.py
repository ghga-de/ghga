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

"""Step definitions for the Data Portal upload journey (admin upload-box screens)."""

import re
import time

from playwright.sync_api import expect

from .conftest import (
    Config,
    JointFixture,
    MongoFixture,
    given,
    parse,
    scenarios,
    then,
    when,
)

scenarios("../features/502_data_portal_uploads.feature")

TIMEOUT = 3000
UI_BOX_TITLE = "TB UI Upload Box {storage}"
STORAGE_LABELS = {"primary": "Primary", "secondary": "Secondary"}

INGEST_INTERVAL, INGEST_TIMEOUT = 3, 30  # seconds


def _box_title(storage_name: str) -> str:
    assert storage_name in STORAGE_LABELS, f"Unknown storage: {storage_name}"
    return UI_BOX_TITLE.format(storage=storage_name)


def _filter_manager_by_title(fixtures: JointFixture, title: str):
    """Open the manager filter (if collapsed) and filter the list by box title."""
    page = fixtures.playwright.page
    main = page.locator("main")
    filter_toggle = page.get_by_role("button", name="Filter upload boxes")
    if filter_toggle.is_visible():
        filter_toggle.click()
    main.get_by_label("Upload box title").first.fill(title)


def _upload_grant_row(fixtures, box_title):
    """Return the row in the grants list for the given box title.

    The row selection here is a bit tricky, there is no clear identifier
    but many "div" elements, so the general text-based selection returns non-unique;
    "div.border-b" is the most sufficient so far.
    """
    page = fixtures.playwright.page
    page.wait_for_selector("app-user-upload-grants-list", timeout=TIMEOUT)
    grants_list = page.locator("app-user-upload-grants-list")
    expect(grants_list).to_be_visible(timeout=TIMEOUT)
    return grants_list.locator("div.border-b").filter(has_text=box_title)


def _files_table(fixtures: JointFixture):
    """Return the files table shown in the upload box details."""
    table = fixtures.playwright.page.locator("app-upload-box-files-table table")
    expect(table).to_be_visible(timeout=TIMEOUT)
    return table


@then("the upload box manager list is displayed")
def check_manager_list(fixtures: JointFixture):
    """Check the Upload Box Manager list/table component is shown."""
    page = fixtures.playwright.page
    expect(page).to_have_url(re.compile(r"/upload-box-manager$"))
    main = page.locator("main")
    expect(main).to_contain_text("Upload Box Manager", timeout=TIMEOUT)
    table = main.locator("table")
    expect(table).to_be_visible(timeout=TIMEOUT)
    expect(table.get_by_text("Title", exact=True).first).to_be_visible()
    expect(table.get_by_text("State", exact=True).first).to_be_visible()


@when(parse('I create an upload box for "{storage_name}" storage via the portal'))
def create_upload_box(storage_name: str, fixtures: JointFixture):
    """Create an upload box through the 'Create Upload Box' dialog."""
    page = fixtures.playwright.page
    title = _box_title(storage_name)

    create_button = page.get_by_role("button", name="Create Upload Box")
    expect(create_button).to_be_visible(timeout=TIMEOUT)
    create_button.click()

    dialog = page.get_by_role("dialog")
    expect(dialog).to_contain_text("Create a new Upload Box", timeout=TIMEOUT)
    dialog.get_by_label("Title").fill(title)
    dialog.get_by_label("Description").fill("Created via archive-test-bed UI journey")
    dialog.get_by_role("combobox", name="Storage location").click()
    page.get_by_role("option", name=STORAGE_LABELS[storage_name]).click()
    dialog.get_by_label("Size limit (in TiB)").fill("1")

    ok_button = dialog.get_by_role("button", name="OK")
    expect(ok_button).to_be_enabled(timeout=TIMEOUT)
    ok_button.click()


@then(parse('the upload box for "{storage_name}" storage is listed'))
def check_box_listed(storage_name: str, fixtures: JointFixture):
    """Confirm the newly created box appears in the manager list by its title."""
    page = fixtures.playwright.page
    title = _box_title(storage_name)
    _filter_manager_by_title(fixtures, title)
    expect(page.locator("main").get_by_text(title)).to_be_visible(timeout=TIMEOUT)


@when(parse('I open the details of the "{storage_name}" upload box in the portal'))
def open_box_details(storage_name: str, fixtures: JointFixture):
    """Open the details page of the box identified by its title."""
    page = fixtures.playwright.page
    title = _box_title(storage_name)
    main = page.locator("main")
    _filter_manager_by_title(fixtures, title)
    details_button = main.get_by_role("button", name="View upload box details").first
    expect(details_button).to_be_visible(timeout=TIMEOUT)
    details_button.click()
    expect(page).to_have_url(re.compile(r"/upload-box-manager/.+"))
    expect(main).to_contain_text(title)


@when(
    parse(
        '"{user_name}" has been granted upload access for the "{storage_name}" upload box'
    )
)
def grant_upload_access(user_name: str, storage_name: str, fixtures: JointFixture):
    """Grant the user upload access from the box details page (Add new upload grant)."""
    page = fixtures.playwright.page
    main = page.locator("main")
    expect(main).to_contain_text(storage_name)

    add_grant = page.get_by_role("button", name="Add new upload grant")
    expect(add_grant).to_be_visible(timeout=TIMEOUT)
    add_grant.click()
    expect(page).to_have_url(re.compile(r"/upload-box-manager/.+/grant/new"))
    expect(main).to_contain_text("New Upload Grant")

    _, name = fixtures.auth.split_title(user_name)

    # Search for the user, then pick them from the result table
    search_field = main.get_by_label("Search by name, email or external ID")
    expect(search_field).to_be_visible(timeout=TIMEOUT)
    search_field.fill(name)
    user_row = main.get_by_role("button").filter(has_text=name)
    expect(user_row.first).to_be_visible(timeout=TIMEOUT)
    user_row.first.click()

    # Selecting the user reveals the "Select an IVA" card
    iva_card = page.locator("mat-card").filter(has_text="Select an IVA")
    expect(iva_card).to_be_visible(timeout=TIMEOUT)
    iva_card.get_by_text(re.compile(r"\bSMS\b")).first.click()

    create_grant = page.get_by_role("button", name="Create Upload Grant")
    expect(create_grant).to_be_visible(timeout=TIMEOUT)
    create_grant.click()
    page.wait_for_load_state()

    # Success returns to the Upload Box Details page with the user listed under
    # grants section
    expect(page).to_have_url(re.compile(r"/upload-box-manager/[^/]+$"))
    grants_card = page.locator("mat-card").filter(
        has=page.get_by_role("heading", level=2, name="Upload Grants")
    )
    expect(grants_card).to_contain_text(name, timeout=TIMEOUT)


@when(parse('I create an upload token for "{storage_name}" storage'))
def create_upload_token(storage_name: str, fixtures: JointFixture):
    """Create an upload token (WPAT) for the box via portal."""
    page = fixtures.playwright.page
    box_title = _box_title(storage_name)
    row = _upload_grant_row(fixtures, box_title)
    row.get_by_role("button", name="Create an upload token for this upload box").click()

    dialog = page.get_by_role("dialog").first
    expect(dialog).to_contain_text("Create an Upload Token", timeout=TIMEOUT)
    expect(dialog).to_contain_text("Selected upload box:")
    expect(dialog).to_contain_text(box_title)

    key_field = (
        dialog.locator("mat-form-field")
        .filter(has_text=re.compile("Crypt4GH", re.IGNORECASE))
        .locator("input")
    )
    expect(key_field).to_be_visible(timeout=TIMEOUT)
    key_field.fill(fixtures.config.user_public_crypt4gh_key)

    generate_button = dialog.get_by_role("button", name="Generate upload token")
    expect(generate_button).to_be_enabled(timeout=TIMEOUT)
    generate_button.click()
    page.wait_for_load_state()

    expect(dialog).to_contain_text(
        "Your upload token has been created", timeout=TIMEOUT
    )
    upload_token = dialog.locator("pre").inner_text().strip()
    id_, token = upload_token.split(":", 1)
    assert 20 <= len(id_) < 40 and 80 < len(token) < 120, "Unexpected token format"
    fixtures.state.set_state(f"upload token for {storage_name}", upload_token)


@then(parse('the upload token for "{storage_name}" storage is available'))
def check_upload_token_available(storage_name: str, fixtures: JointFixture):
    """Confirm an upload token for the storage has been stored in state."""
    token = fixtures.state.get_state(f"upload token for {storage_name}")
    assert token, f"No upload token stored for {storage_name} storage"


@when(parse('I submit the upload for "{storage_name}" storage'))
def submit_upload(storage_name: str, fixtures: JointFixture):
    """Submit/lock the upload from the profile page (moves the box to 'Locked')."""
    page = fixtures.playwright.page
    box_title = _box_title(storage_name)
    row = _upload_grant_row(fixtures, box_title)
    row.get_by_role("button", name="Submit this upload box as complete").click()
    dialog = page.get_by_role("dialog")
    expect(dialog).to_contain_text("Submit upload box?", timeout=TIMEOUT)
    confirm_button = dialog.get_by_role("button", name=re.compile("Submit"))
    confirm_button.click()
    page.wait_for_load_state()

    # After submitting, the box is locked and leaves the open-boxes list.
    expect(row).to_have_count(0)


@then(
    parse(
        'the files uploaded to "{storage_name}" storage are listed in "{direction}" order'
    )
)
def check_files_order(storage_name: str, direction: str, fixtures: JointFixture):
    """Check the file name column lists the box's files in the given order."""
    assert direction in ("ascending", "descending"), f"Unknown order: {direction}"
    files = fixtures.state.get_state(f"rdub_{storage_name}_files")
    assert files, f"No uploaded files found in state for storage '{storage_name}'"
    aliases = sorted(
        (str(file["alias"]) for file in files), reverse=direction == "descending"
    )

    table = _files_table(fixtures)
    rows = table.locator("tbody tr")
    expect(rows).to_have_count(len(files), timeout=TIMEOUT)
    # The paginator only appears when the box holds more files than fit one page
    paginator = fixtures.playwright.page.get_by_label("Select page of files")
    expect(paginator).to_have_count(0)
    for index, alias in enumerate(aliases):
        expect(rows.nth(index).locator("td").first).to_have_text(alias, timeout=TIMEOUT)


@then(
    parse(
        'the files uploaded to "{storage_name}" storage can be sorted '
        'by file name in "{direction}" order'
    )
)
def sort_files_and_check_order(
    storage_name: str, direction: str, fixtures: JointFixture
):
    """Sort the files table by file name via its column header and check the order.

    The file list starts out in ascending name order (the server default), so a
    single click on the header requests the descending order.
    """
    assert direction == "descending", f"Unsupported sort direction: {direction}"
    page = fixtures.playwright.page
    header = _files_table(fixtures).get_by_role("columnheader", name="Filename")
    expect(header).to_be_visible(timeout=TIMEOUT)
    # The reordered list must be requested from the server, not sorted locally
    with page.expect_response(
        lambda response: "/uploads" in response.url and "sort=-alias" in response.url
    ) as response_info:
        header.click()
    assert response_info.value.ok, (
        f"Sorting the file list failed: {response_info.value.status}"
    )
    check_files_order(storage_name, direction, fixtures)


@then(parse('the uploaded files for "{dataset_alias}" are listed in the upload box'))
def check_uploaded_files_in_box(
    dataset_alias: str, fixtures: JointFixture, file_fixture: dict
):
    """Confirm the uploaded files appear in the box's 'Storage & Files' card."""
    page = fixtures.playwright.page
    storage_card = page.locator("mat-card").filter(
        has=page.get_by_role("heading", level=2, name="Storage & Files")
    )
    expect(storage_card).to_be_visible(timeout=TIMEOUT)
    file_batch = file_fixture[dataset_alias]
    for object_id, _path in file_batch.file_info:
        expect(storage_card).to_contain_text(object_id, timeout=TIMEOUT)


@when(parse('I select the study "{dataset_alias}" in the mapping tool'))
def select_study_in_mapping_tool(dataset_alias: str, fixtures: JointFixture):
    """Select the dataset's study in the mapping tool's Study dropdown (auto-maps)."""
    page = fixtures.playwright.page
    datasets = fixtures.state.get_state("all available datasets")
    assert dataset_alias in datasets, f"Dataset '{dataset_alias}' not found in state"
    # TODO: verify the study accession key path in the stored dataset details.
    study = datasets[dataset_alias]["details"]["study"]
    study_accession = study.get("accession")
    assert study_accession, "Study accession not found in state for the dataset"

    page = fixtures.playwright.page
    study_card = page.locator("mat-card").filter(
        has=page.get_by_role("heading", level=2, name="Study")
    )
    expect(study_card).to_contain_text("Please select the study", timeout=TIMEOUT)
    study_card.get_by_role("combobox").first.click()
    page.get_by_role(
        "option", name=re.compile(re.escape(study_accession))
    ).first.click()


@then(parse('the file mapping is complete for "{dataset_alias}"'))
def check_mapping_complete(dataset_alias: str, fixtures: JointFixture):
    """After selecting the study, the test-bed files auto-map 1:1 (nothing unmapped)."""
    all_datasets = fixtures.state.get_state("all available datasets")
    file_count = len(all_datasets[dataset_alias]["details"]["files"])

    page = fixtures.playwright.page
    info_card = page.locator("mat-card").filter(
        has=page.get_by_role("heading", level=2, name="Upload Box Info")
    )

    expect(info_card).to_contain_text("Locked", timeout=TIMEOUT)
    content_card = page.locator("mat-card-content")

    # The file states advance on the server as ingestion progresses, but the
    # view does not poll on its own — re-fetch the file list with the refresh
    # button until all files are re-encrypted.
    refresh_button = page.get_by_role("button", name="Refresh the upload box details")
    expect(refresh_button).to_be_visible(timeout=TIMEOUT)

    slept: int = 0
    while slept < INGEST_TIMEOUT:
        if content_card.get_by_text("re-encrypted").count() == file_count:
            break
        with page.expect_response(lambda response: "/uploads" in response.url):
            refresh_button.click()
        time.sleep(INGEST_INTERVAL)
        slept += INGEST_INTERVAL
    expect(content_card.get_by_text("re-encrypted")).to_have_count(file_count)

    mapping_card = page.locator("mat-card").filter(
        has=page.get_by_role("heading", level=2, name="File Mapping")
    )
    expect(mapping_card).to_be_visible(timeout=TIMEOUT)
    mapping_card.get_by_text(re.compile(r"\bFile\salias\b")).first.click()

    expect(mapping_card).to_contain_text(
        re.compile(rf"Matches:\s*{file_count}"), timeout=TIMEOUT
    )


@when("I confirm the mapping and archive the upload box")
def confirm_and_archive(fixtures: JointFixture):
    """Confirm the mapping and archive the box (mapping tool -> confirm dialog)."""
    page = fixtures.playwright.page
    confirm_button = page.get_by_role("button", name="Confirm mapping and archive")
    expect(confirm_button).to_be_enabled(timeout=TIMEOUT)
    confirm_button.click()

    dialog = page.get_by_role("dialog", name="Confirm Mapping and Archive")
    expect(dialog).to_be_visible(timeout=TIMEOUT)
    checkbox = dialog.get_by_role(
        "checkbox", name="I understand this action cannot be undone"
    )
    expect(checkbox).to_be_visible(timeout=TIMEOUT)
    checkbox.check()
    expect(checkbox).to_be_checked()
    archive_button = dialog.get_by_role("button", name="Confirm and Archive")
    expect(archive_button).to_be_enabled(timeout=TIMEOUT)

    # The initiation of the next step aborts the in-flight request before the
    # backend archives the box. We need wait for actual response itself
    # so the archive request lands, and surface its status.
    def _is_archive(response):
        print(f"{response.request.method} {response.url} -> {response.status}")
        return "/upload-boxes/" in response.url and response.request.method == "PATCH"

    with page.expect_response(_is_archive) as response_info:
        archive_button.click()
    response = response_info.value
    assert response.ok, f"Archive request failed: {response.status} {response.url}"


@then(parse('the "{storage_name}" upload box is archived in the portal'))
def check_box_archived(storage_name: str, fixtures: JointFixture):
    """Confirm the box shows the Archived state and accessions are now present."""
    page = fixtures.playwright.page
    info_card = page.locator("mat-card").filter(
        has=page.get_by_role("heading", level=2, name="Upload Box Info")
    )
    expect(info_card).to_contain_text("State:", timeout=TIMEOUT)
    expect(info_card).to_contain_text(storage_name, timeout=TIMEOUT)

    # The state change may not be reflected immediately in the UI, so we
    # re-fetch the box with the refresh button until "Archived" appears.
    refresh_button = page.get_by_role("button", name="Refresh the upload box details")
    slept: int = 0
    while slept < INGEST_TIMEOUT:
        if info_card.get_by_text("Archived").is_visible():
            return
        expect(refresh_button).to_be_enabled(timeout=TIMEOUT)
        with page.expect_response(
            lambda response: (
                "/upload-boxes/" in response.url and response.request.method == "GET"
            )
        ):
            refresh_button.click()
        time.sleep(INGEST_INTERVAL)
        slept += INGEST_INTERVAL
    raise AssertionError(
        f"Upload box for {storage_name} storage did not reach 'Archived' state after"
    )
