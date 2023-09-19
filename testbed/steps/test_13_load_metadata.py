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
#

"""Step definitions for loading metadata artifacts with the datasteward-kit"""

import subprocess
from collections import Counter

from ghga_datasteward_kit.loading import LoadConfig

from steps.utils import load_config_as_file, temporary_file

from .conftest import Config, JointFixture, MongoFixture, scenarios, then, when

scenarios("../features/13_load_metadata.feature")


@when("metadata is loaded into the system")
def run_the_load_command(fixtures: JointFixture):
    load_config_path = load_config_as_file(
        LoadConfig(
            event_store_path=fixtures.dsk.config.event_store,
            artifact_topic_prefix="artifact",
            artifact_types=["embedded_public", "stats_public"],
            loader_api_root=fixtures.config.metldata_url,
        )
    )

    loader_token = fixtures.auth.read_simple_token()
    with temporary_file(fixtures.config.dsk_token_path, loader_token):
        completed_upload = subprocess.run(  # nosec B607, B603
            [
                "ghga-datasteward-kit",
                "load",
                "--config-path",
                load_config_path,
            ],
            capture_output=True,
            check=True,
            encoding="utf-8",
            text=True,
            timeout=10 * 60,
        )

        assert not completed_upload.stdout
        assert not completed_upload.stderr


@then("the stats for the datasets exist in the database")
def check_stats_in_metldata_database(config: Config, mongo: MongoFixture):
    datasets = mongo.wait_for_documents(
        config.metldata_db_name, "art_stats_public_class_DatasetStats", {}
    )
    assert datasets
    assert len(datasets) == 6  # 4 from minimal and 2 from complete example
    simplified_datasets = {}
    for dataset in datasets:
        accession = dataset["_id"]
        assert accession.startswith("GHGAD")
        content = dataset["content"]
        assert content["accession"] == accession
        simplified_dataset = {
            "types": ", ".join(content["types"]),
            "files": content["files_summary"]["count"],
            "studies": content["studies_summary"]["count"],
        }
        simplified_datasets[content["title"]] = simplified_dataset
    assert simplified_datasets == {
        "The A dataset": {"types": "Another Type, A Type", "files": 16, "studies": 1},
        "The B dataset": {"types": "And another Type", "files": 6, "studies": 1},
        "The C dataset": {
            "types": "A Type, And yet another Type",
            "files": 20,
            "studies": 2,
        },
        "The D dataset": {"types": "A Type", "files": 10, "studies": 1},
        "The complete-A dataset": {
            "types": "Another Type, A Type",
            "files": 7,
            "studies": 1,
        },
        "The complete-B dataset": {
            "types": "And another Type",
            "files": 12,
            "studies": 1,
        },
    }


@then("the test datasets exist as embedded dataset in the database")
def check_datasets_in_metldata_database(config: Config, mongo: MongoFixture):
    datasets = mongo.wait_for_documents(
        config.metldata_db_name, "art_embedded_public_class_EmbeddedDataset", {}
    )
    assert datasets
    assert len(datasets) == 6  # 4 from minimal and 2 from complete example
    simplified_datasets = {}
    for dataset in datasets:
        accession = dataset["_id"]
        assert accession.startswith("GHGAD")
        content = dataset["content"]
        assert content["accession"] == accession
        simplified_dataset = {
            "title": content["title"],
            "description": content["description"],
            "study_files": len(content["study_files"]),
        }
        simplified_datasets[content["alias"]] = simplified_dataset
    assert simplified_datasets == {
        "DS_1": {
            "description": "An interesting dataset A",
            "study_files": 16,
            "title": "The A dataset",
        },
        "DS_2": {
            "description": "An interesting dataset B",
            "study_files": 6,
            "title": "The B dataset",
        },
        "DS_3": {
            "description": "An interesting dataset C",
            "study_files": 20,
            "title": "The C dataset",
        },
        "DS_4": {
            "description": "An interesting dataset D",
            "study_files": 10,
            "title": "The D dataset",
        },
        "DS_A": {
            "description": "An interesting dataset A of complete example set",
            "study_files": 1,
            "title": "The complete-A dataset",
        },
        "DS_B": {
            "description": "An interesting dataset B of complete example set",
            "study_files": 0,
            "title": "The complete-B dataset",
        },
    }


@then("the test datasets are known to the work package service")
def check_datasets_in_wps_database(config: Config, mongo: MongoFixture):
    datasets = mongo.wait_for_documents(config.wps_db_name, "datasets", {})
    assert datasets
    assert len(datasets) == 6
    simplified_datasets = {}
    for dataset in datasets:
        accession = dataset.get("_id")
        assert isinstance(accession, str)
        assert accession.startswith("GHGAD")
        assert dataset.get("stage") == "download"
        title = dataset.get("title")
        assert title
        description = dataset.get("description")
        files = dataset.get("files")
        assert isinstance(files, list)
        assert all(isinstance(file_.get("id"), str) for file_ in files)
        assert all(file_["id"].startswith("GHGAF") for file_ in files)
        extensions = Counter(file.get("extension") for file in files)
        simplified_datasets[title] = {"description": description, "files": extensions}
    assert simplified_datasets == {
        "The A dataset": {
            "description": "An interesting dataset A",
            "files": Counter({".fastq.gz": 16}),
        },
        "The B dataset": {
            "description": "An interesting dataset B",
            "files": Counter({".fastq.gz": 6}),
        },
        "The C dataset": {
            "description": "An interesting dataset C",
            "files": Counter({".fastq.gz": 20}),
        },
        "The D dataset": {
            "description": "An interesting dataset D",
            "files": Counter({".fastq.gz": 10}),
        },
        "The complete-A dataset": {
            "description": "An interesting dataset A of complete example set",
            "files": Counter({".fastq.gz": 4, ".vcf.gz": 3}),
        },
        "The complete-B dataset": {
            "description": "An interesting dataset B of complete example set",
            "files": Counter({".fastq.gz": 6, ".vcf.gz": 6}),
        },
    }
