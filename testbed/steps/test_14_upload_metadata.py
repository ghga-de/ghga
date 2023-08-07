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

from ghga_datasteward_kit.loading import LoadConfig

from steps.utils import load_config_as_file

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

    completed_upload = subprocess.run(  # nosec B607, B603
        [
            "ghga-datasteward-kit",
            "load",
            "--config-path",
            load_config_path,
        ],
        capture_output=True,
        input=loader_token,
        check=True,
        encoding="utf-8",
        text=True,
        timeout=10 * 60,
    )

    assert (
        "Please paste the token used to authenticate against the loader API:"
        in completed_upload.stdout
    )
    assert not completed_upload.stderr


@then("the test dataset exists as embedded dataset in the database")
def check_metldata_database(config: Config, mongo: MongoFixture):
    datasets = mongo.wait_for_documents(
        config.metldata_db_name, "art_embedded_public_class_EmbeddedDataset", {}
    )
    assert datasets and len(datasets) == 2
    dataset = datasets[0]
    content = dataset.get("content")
    assert content
    assert content.get("title") == "The A dataset"
    study_files = content.get("study_files")
    assert study_files and len(study_files) == 1
    study_filenames = sorted(study_file.get("name") for study_file in study_files)
    assert study_filenames == ["STUDY_1_SPECIMEN_1_FILE_1.fastq.gz"]
    file_accessions = {study_file.get("accession") for study_file in study_files}
    assert len(file_accessions) == 1
    assert all(accession.startswith("GHGAF") for accession in file_accessions)
