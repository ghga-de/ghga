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

scenarios("../features/500_data_portal_browse.feature")

EXPECTED_STATS = {
    "Total datasets": 2,
    "Individuals": 1,
    "Files": 14,
}


@then("the global statistics are available")
def check_global_statistics(playwright: PlaywrightFixture):
    """Check the global statistics on homepage."""
    main = playwright.page.locator("main")
    expect(main).to_contain_text("Statistics")
    expect(main).to_contain_text(f"Total datasets: {EXPECTED_STATS['Total datasets']}")
    expect(main).to_contain_text(f"Individuals: {EXPECTED_STATS['Individuals']}")
    expect(main).to_contain_text(f"Files: {EXPECTED_STATS['Files']}")


@when("I clear the applied filters")
def clear_filters(playwright: PlaywrightFixture):
    button = playwright.page.locator("form").get_by_role("button").get_by_text("Clear")
    button.click()


@then(parse('the summary of the "{dataset_name}" dataset is displayed'))
def check_dataset_summary(
    dataset_name: str, fixtures: JointFixture, playwright: PlaywrightFixture
):
    expect(playwright.page).to_have_url(re.compile(r"/browse$"))
    all_datasets = fixtures.state.get_state("all available datasets")
    dataset = all_datasets[dataset_name]
    main = playwright.page.locator("main")
    expect(main).to_contain_text(dataset["details"]["description"])
    expect(main).to_contain_text(f"{len(dataset['details']['files'])} Files")
    # expect(main).to_contain_text(f"EGA ID: {dataset['details']['ega_accession']}") FIXME


@then(parse('the details of the "{dataset_name}" dataset are displayed'))
def check_dataset_detail(
    dataset_name: str, fixtures: JointFixture, playwright: PlaywrightFixture
):
    """Check the detail page of the dataset."""
    all_datasets = fixtures.state.get_state("all available datasets")
    dataset = all_datasets[dataset_name]
    dataset_accession = dataset["accession"]
    expect(playwright.page).to_have_url(re.compile(rf"/dataset/{dataset_accession}$"))
    page_title = f"Dataset {dataset['accession']} | GHGA Data Portal"
    expect(playwright.page).to_have_title(page_title)
    main = playwright.page.locator("main")
    expect(main).not_to_contain_text("Total Datasets:")
    expect(main).to_contain_text(re.compile("list of experiments", re.IGNORECASE))
    expect(main).to_contain_text(re.compile("list of samples", re.IGNORECASE))

    # url = f"{fixtures.config.dins_url}/dataset_information/{dataset_accession}"
    # response = fixtures.http.get(url)
    # dataset_information = response.json()
    # # TODO add the total size of the files
    # expect(main).to_contain_text(
    #     f"Files Summary ({len(dataset['details']['files'])} files,"
    # )

    main.get_by_role("tab").get_by_text("Publications").click()
    expect(main).to_contain_text("Journal")
    for publication in dataset["details"]["study"]["publications"]:
        expect(main).to_contain_text(publication["title"])

    main.get_by_role("tab").get_by_text("DAP/DAC").click()
    expect(main).to_contain_text("Data Access Committee")
    expect(main).to_contain_text(
        dataset["details"]["data_access_policy"]["alias"].replace("_", " ")
    )
    expect(main).to_contain_text(
        dataset["details"]["data_access_policy"]["data_access_committee"]["email"]
    )

    expect(main).not_to_contain_text("File ID")
    expect(main).not_to_contain_text(min(dataset["details"]["files"]))
    expect(main).not_to_contain_text("Sample ID")
    expect(main).not_to_contain_text("Biospeciment type")
    expect(main).not_to_contain_text("Experiment ID")
    expect(main).not_to_contain_text("Tissue")


@when(parse('I filter datasets by "{filter_option}"'))
def apply_filter(filter_option: str, playwright: PlaywrightFixture):
    """Apply the given filter."""
    expect(playwright.page).to_have_url(re.compile(r"/browse$"))
    checkbox = playwright.page.get_by_label(filter_option).first
    expect(checkbox).to_be_visible()
    expect(checkbox).not_to_be_checked()
    checkbox.check()
    expect(checkbox).to_be_checked()

    playwright.page.locator("form").get_by_role("button").last.click()  # Submit form
    expect(playwright.page).to_have_url(re.compile(rf"{filter_option}"))


@when(parse('I search for "{search_option}"'))
def apply_search(
    search_option: str, fixtures: JointFixture, playwright: PlaywrightFixture
):
    """Apply the given filter."""
    expect(playwright.page).to_have_url(re.compile(r"/browse$"))
    input_box = playwright.page.get_by_placeholder("Enter any keyword or ID").first
    expect(input_box).to_be_visible()
    input_box.fill(search_option)

    playwright.page.locator("form").get_by_role("button").last.click()  # Submit form
    expect(playwright.page).to_have_url(re.compile(rf"{search_option}"))


@then(parse('only the "{dataset_name}" dataset is displayed'))
def check_filtered_dataset(
    dataset_name: str, fixtures: JointFixture, playwright: PlaywrightFixture
):
    """Check the filtered dataset."""
    all_datasets = fixtures.state.get_state("all available datasets")
    dataset = all_datasets[dataset_name]
    main = playwright.page.locator("main")
    expect(main).to_contain_text("Total Datasets:1")
    accordion_list = playwright.page.locator(".mat-accordion")
    assert accordion_list.get_by_role("button").count() == 1
    expect(main).to_contain_text(dataset["title"])


@then(parse('the summary tables for the "{dataset_name}" dataset are displayed'))
def check_files_summary(
    dataset_name: str,
    fixtures: JointFixture,
    playwright: PlaywrightFixture,
):
    """Check the files summary of the dataset."""
    main = playwright.page.locator("main")
    all_datasets = fixtures.state.get_state("all available datasets")
    dataset = all_datasets[dataset_name]

    summaries = [
        ("list of files", "File ID", dataset["details"]["files"]),
        (
            "list of samples",
            "Sample ID",
            [i["accession"] for i in dataset["details"]["samples"]],
        ),
        (
            "list of experiments",
            "Experiment ID",
            [i["accession"] for i in dataset["details"]["experiments"]],
        ),
    ]

    for summary in summaries:
        main.get_by_role("button").get_by_text(
            re.compile(summary[0], re.IGNORECASE)
        ).click()
        expect(main).to_contain_text(summary[1])
        for item in summary[2]:
            expect(main).to_contain_text(item)
