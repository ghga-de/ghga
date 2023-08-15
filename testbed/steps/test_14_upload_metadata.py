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


"""Step definitions for metadata upload tests"""

import subprocess
from collections import Counter

from ghga_datasteward_kit.loading import LoadConfig

from steps.utils import load_config_as_file, temporary_file

from .conftest import Config, JointFixture, MongoFixture, scenarios, then, when

scenarios("../features/14_upload_metadata.feature")


@when("metadata is loaded into the system")
def run_the_load_command(fixtures: JointFixture):
    load_config_path = load_config_as_file(
        LoadConfig(
            event_store_path=fixtures.dsk.config.event_store,
            artifact_topic_prefix="artifact",
            artifact_types=["embedded_public"],
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


@then("the test datasets exist as embedded dataset in the database")
def check_metldata_database(config: Config, mongo: MongoFixture):
    datasets = mongo.wait_for_documents(
        config.metldata_db_name, "art_embedded_public_class_EmbeddedDataset", {}
    )
    assert datasets and len(datasets) == 2
    datasets.sort(key=lambda x: x.get("content", {}).get("title", "None"))
    for num_dataset, dataset in enumerate(datasets):
        content = dataset.get("content")
        assert isinstance(content, dict)
        accession = content.get("accession")
        assert isinstance(accession, str)
        assert accession.startswith("GHGAD")
        assert content.get("alias") == f"DS_{num_dataset + 1}"
        assert content.get("title") == f"The {num_dataset + 65:c} dataset"
        assert (
            content.get("description") == f"An interesting dataset {num_dataset + 65:c}"
        )
        analysis_files = content.get("analysis_process_output_files")
        assert isinstance(analysis_files, list)
        sequencing_files = content.get("sequencing_process_files")
        assert isinstance(sequencing_files, list)
        study_files = content.get("study_files")
        assert isinstance(study_files, list)
        if num_dataset == 1:
            assert not study_files
            assert len(analysis_files) == 6
            assert len(sequencing_files) == 6
        else:
            assert study_files and len(study_files) == 1
            study_file = study_files[0]
            assert study_file.pop("accession").startswith("GHGAF")
            assert study_file.pop("dataset") == accession
            assert isinstance(study_file.pop("study"), dict)
            assert study_file == {
                "alias": "STUDY_FILE_1",
                "checksum": "7a586609dd8c7d6f53cbc2e82e1165de"
                "2c7aab6769c6dde9882b45048b0fdaa9",
                "checksum_type": "SHA256",
                "format": "FASTQ",
                "forward_or_reverse": "REVERSE",
                "name": "STUDY_1_SPECIMEN_1_FILE_1.fastq.gz",
                "size": 106497,
            }
            assert len(analysis_files) == 3


@then("the test datasets are known to the work package service")
def check_wps_database(config: Config, mongo: MongoFixture):
    datasets = mongo.wait_for_documents(config.wps_db_name, "datasets", {})
    assert datasets and len(datasets) == 2
    datasets.sort(key=lambda x: x.get("title", "None"))
    for num_dataset, dataset in enumerate(datasets):
        accession = dataset.get("_id")
        assert isinstance(accession, str)
        assert accession.startswith("GHGAD")
        assert dataset.get("title") == f"The {num_dataset + 65:c} dataset"
        assert (
            dataset.get("description") == f"An interesting dataset {num_dataset + 65:c}"
        )
        assert dataset.get("stage") == "download"
        files = dataset.get("files")
        assert isinstance(files, list)
        assert all(isinstance(file.get("id"), str) for file in files)
        assert all(file["id"].startswith("GHGAF") for file in files)
        found_extensions = Counter(file.get("extension") for file in files)
        expected_extensions = (
            {".fastq.gz": 6, ".vcf.gz": 6}
            if num_dataset == 1
            else {".fastq.gz": 4, ".vcf.gz": 3}
        )
        assert found_extensions == expected_extensions
