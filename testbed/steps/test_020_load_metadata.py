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

"""Step definitions for loading metadata artifacts with the datasteward-kit"""

from collections import Counter

from fixtures.utils import temporary_file
from ghga_datasteward_kit.loading import LoadConfig

from steps.utils import (
    is_alias_accession,
    is_dataset_pid,
    is_legacy_accession,
    is_study_pid,
    load_config_as_file,
    read_submission,
    run_dskit,
)

from .conftest import Config, JointFixture, MongoFixture, scenarios, then, when

scenarios("../features/020_load_metadata.feature")


@when("metadata is loaded into the system")
def run_the_load_command(fixtures: JointFixture):
    load_config_path = load_config_as_file(
        LoadConfig(
            event_store_path=fixtures.dsk.config.event_store,
            artifact_topic_prefix="artifact",
            artifact_types=["embedded_public", "stats_public", "added_accessions"],
            publishable_artifacts=["added_accessions"],
            loader_api_root=fixtures.config.metldata_url,
        )
    )

    upload_token = fixtures.config.upload_token
    with temporary_file(fixtures.config.dsk_token_path, upload_token):
        completed_upload = run_dskit("load", "--config-path", load_config_path)

        assert not completed_upload.stdout
        assert not "ERROR" in completed_upload.stderr
        assert not completed_upload.returncode


def legacy_accession_map(fixtures: JointFixture) -> dict:
    """Get the accession map of study X from its amended submission."""
    submission_id = fixtures.state.get_state(
        f"submission id {fixtures.dsk.config.legacy_metadata_path.stem}"
    )
    return read_submission(fixtures, submission_id)["accession_map"]


@then("the stats for the datasets exist in the database")
def check_stats_in_metldata_database(
    fixtures: JointFixture, config: Config, mongo: MongoFixture
):
    datasets = mongo.wait_for_documents(
        config.metldata_db_name, "art_stats_public_class_DatasetStats", {}, number=3
    )
    assert datasets
    assert len(datasets) == 3  # A and B from the example metadata, X amended
    # the embedded dataset step sets "dataset_accessions" only after this one
    legacy_accession = legacy_accession_map(fixtures)["datasets"]["DS_X"]
    simplified_datasets = {}
    for dataset in datasets:
        accession = dataset["_id"]
        legacy = accession == legacy_accession
        assert (is_legacy_accession if legacy else is_dataset_pid)(accession)
        content = dataset["content"]
        assert content["accession"] == accession
        simplified_dataset = {
            "types": ", ".join(content["types"]),
            "files": content["files_summary"]["count"],
            "studies": content["studies_summary"]["count"],
        }
        simplified_datasets[content["title"]] = simplified_dataset
    assert simplified_datasets == {
        "The complete-A dataset": {
            "types": "Another Type, A Type",
            "files": 7,
            "studies": 1,
        },
        "The complete-B dataset": {
            "types": "And another Type",
            "files": 7,
            "studies": 1,
        },
        "The complete-X dataset": {
            "types": "And another Type",
            "files": 2,
            "studies": 1,
        },
    }


@then("the test datasets exist as embedded dataset in the database")
def check_datasets_in_metldata_database(
    fixtures: JointFixture, config: Config, mongo: MongoFixture
):
    datasets = mongo.wait_for_documents(
        config.metldata_db_name,
        "art_embedded_public_class_EmbeddedDataset",
        {},
        number=3,
    )
    assert datasets
    assert len(datasets) == 3  # A and B from the example metadata, X amended
    simplified_datasets = {}
    for dataset in datasets:
        accession = dataset["_id"]
        assert is_dataset_pid(accession) or is_legacy_accession(accession)
        content = dataset["content"]
        assert content["accession"] == accession
        simplified_dataset = {
            "title": content["title"],
            "description": content["description"],
            "files": len(content["files"]),
        }
        simplified_datasets[content["alias"]] = simplified_dataset
    assert simplified_datasets == {
        "DS_A": {
            "description": "An interesting dataset A of complete example set",
            "files": 7,
            "title": "The complete-A dataset",
        },
        "DS_B": {
            "description": "An interesting dataset B of complete example set",
            "files": 7,
            "title": "The complete-B dataset",
        },
        "DS_X": {
            "description": "An interesting dataset X of complete example set",
            "files": 2,
            "title": "The complete-X dataset",
        },
    }
    accession_map = {
        d["content"]["alias"]: {
            "dataset_accession": d["content"]["accession"],
            "study_accession": d["content"]["study"]["accession"],
            "ega_accession": d["content"]["ega_accession"],
        }
        for d in datasets
    }
    assert "DS_A" in accession_map
    assert "DS_B" in accession_map
    assert "DS_X" in accession_map
    fixtures.state.set_state("dataset_accessions", accession_map)


@then("the test datasets are known to the work package service")
def check_datasets_in_wps_database(
    fixtures: JointFixture, config: Config, mongo: MongoFixture
):
    datasets = mongo.wait_for_documents(config.wps_db_name, "datasets", {}, number=3)
    assert datasets
    assert len(datasets) == 3
    dataset_accessions = fixtures.state.get_state("dataset_accessions")
    legacy_accession = dataset_accessions["DS_X"]["dataset_accession"]
    simplified_datasets = {}
    for dataset in datasets:
        accession = dataset.get("_id")
        assert isinstance(accession, str)
        legacy = accession == legacy_accession
        assert (is_legacy_accession if legacy else is_dataset_pid)(accession)
        assert dataset.get("stage") == "download"
        title = dataset.get("title")
        assert title
        description = dataset.get("description")
        files = dataset.get("files")
        assert isinstance(files, list)
        assert all(isinstance(file_.get("accession"), str) for file_ in files)
        is_file_accession = is_legacy_accession if legacy else is_alias_accession
        assert all(is_file_accession(file_["accession"]) for file_ in files)
        extensions = Counter(file.get("extension") for file in files)
        simplified_datasets[title] = {"description": description, "files": extensions}
    assert simplified_datasets == {
        "The complete-A dataset": {
            "description": "An interesting dataset A of complete example set",
            "files": Counter({".fastq.gz": 3, ".vcf.gz": 2, ".json": 1, ".txt": 1}),
        },
        "The complete-B dataset": {
            "description": "An interesting dataset B of complete example set",
            "files": Counter({".fastq.gz": 6, ".txt": 1}),
        },
        "The complete-X dataset": {
            "description": "An interesting dataset X of complete example set",
            "files": Counter({".fastq.gz": 2}),
        },
    }


@then("the test datasets are known to the access request service")
def check_datasets_in_ars_database(
    fixtures: JointFixture, config: Config, mongo: MongoFixture
):
    datasets = mongo.wait_for_documents(config.ars_db_name, "datasets", {}, number=3)
    assert datasets
    assert len(datasets) == 3
    dataset_accessions = fixtures.state.get_state("dataset_accessions")
    legacy_accession = dataset_accessions["DS_X"]["dataset_accession"]
    simplified_datasets = {}
    for dataset in datasets:
        accession = dataset.get("_id")
        assert isinstance(accession, str)
        legacy = accession == legacy_accession
        assert (is_legacy_accession if legacy else is_dataset_pid)(accession)
        title = dataset.get("title")
        assert title
        description = dataset.get("description")
        assert description
        dac_alias = dataset.get("dac_alias")
        assert dac_alias
        dac_email = dataset.get("dac_email")
        assert dac_alias
        simplified_datasets[title] = {
            "description": description,
            "dac_alias": dac_alias,
            "dac_email": dac_email,
        }
    assert simplified_datasets == {
        "The complete-A dataset": {
            "description": "An interesting dataset A of complete example set",
            "dac_alias": "DAC_1",
            "dac_email": "dac_institute_a@dac.dac",
        },
        "The complete-B dataset": {
            "description": "An interesting dataset B of complete example set",
            "dac_alias": "DAC_1",
            "dac_email": "dac_institute_a@dac.dac",
        },
        "The complete-X dataset": {
            "description": "An interesting dataset X of complete example set",
            "dac_alias": "DAC_X",
            "dac_email": "dac_institute_a@dac.dac",
        },
    }


@then("only the legacy dataset carries flat accessions")
def check_accession_schemes(
    fixtures: JointFixture, config: Config, mongo: MongoFixture
):
    # named per dataset, so a PID study getting flat accessions fails instead of
    # passing a check that accepts either scheme
    accession_map = legacy_accession_map(fixtures)
    dataset_accession = accession_map["datasets"]["DS_X"]
    study_accession = accession_map["studies"]["STUDY_X"]
    file_accessions = set(accession_map["research_data_files"].values())
    assert is_legacy_accession(dataset_accession)
    assert is_legacy_accession(study_accession)
    assert file_accessions and all(map(is_legacy_accession, file_accessions))

    dataset = mongo.wait_for_document(
        config.metldata_db_name,
        "art_embedded_public_class_EmbeddedDataset",
        {"_id": dataset_accession},
        extend_mapping=False,  # the _id field type is string, not UUID
    )
    assert dataset
    content = dataset["content"]
    assert content["alias"] == "DS_X"
    assert content["study"]["accession"] == study_accession
    # the embedded dataset lists its files as plain accessions
    assert set(content["files"]) == file_accessions

    dataset_accessions = fixtures.state.get_state("dataset_accessions")
    for alias in ("DS_A", "DS_B"):
        assert is_dataset_pid(dataset_accessions[alias]["dataset_accession"])
        assert is_study_pid(dataset_accessions[alias]["study_accession"])
