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

"""Step definitions for ingesting existing files again"""

import json
import subprocess
from datetime import datetime
from pathlib import Path

from ghga_datasteward_kit.file_ingest import IngestConfig

from steps.test_120_upload_files import call_data_steward_kit_ingest
from steps.utils import ingest_config_as_file

from .conftest import JointFixture, given, scenarios, then, when

scenarios("../features/121_ingest_existing_files_again.feature")


def restore_file_metadata_json(file_metadata_dir: Path, file_metadata: dict):
    file_metadata_dir.mkdir(exist_ok=True)
    file_alias = file_metadata["Alias"]
    metadata_file_path = file_metadata_dir / f"{file_alias}.json"
    with metadata_file_path.open("w") as metadata_file:
        json.dump(file_metadata, metadata_file)
    assert metadata_file_path.exists()


@given("all the file metadata is stored in the internal file registry")
def check_metadata_documents(fixtures: JointFixture):
    file_information = fixtures.state.get_state("all file information") or {}
    accessions = list(file_information)
    documents = fixtures.mongo.wait_for_documents(
        db_name=fixtures.config.ifrs_db_name,
        collection_name=fixtures.config.ifrs_metadata_collection,
        query={"_id": {"$in": accessions}},
        number=len(accessions),
    )
    assert documents

    document = fixtures.mongo.wait_for_documents(
        db_name=fixtures.config.fis_db_name,
        collection_name=fixtures.config.fis_ingested_files_collection,
        query={"_id": {"$in": accessions}},
        number=len(accessions),
    )
    assert document


@when(
    "an existing file is attempted to be ingested again",
    target_fixture="ingest_output",
)
def ingest_existing_file_again(fixtures: JointFixture) -> subprocess.CompletedProcess:
    """Ingest an already existing file again.

    Retrieve the first file in the stored file information list,
    restore the file metadata JSON and ingest it again
    """
    all_file_information = fixtures.state.get_state("all file information") or {}

    file_accession = min(all_file_information)
    file_metadata = all_file_information[file_accession]

    file_metadata_dir = fixtures.dsk.config.file_metadata_dir
    restore_file_metadata_json(file_metadata_dir, file_metadata=file_metadata)

    ingest_config = IngestConfig(
        file_ingest_baseurl=fixtures.config.fis_url,
        file_ingest_pubkey=fixtures.config.fis_pubkey,
        input_dir=fixtures.dsk.config.file_metadata_dir,
        submission_store_dir=fixtures.dsk.config.submission_store,
        map_files_fields=list(fixtures.dsk.config.metadata_file_fields),
        selected_storage_alias=file_metadata["Storage alias"],
        fallback_bucket_id=file_metadata["Bucket ID"],
    )

    ingest_config_path = ingest_config_as_file(config=ingest_config)

    return call_data_steward_kit_ingest(
        ingest_config_path=ingest_config_path,
        token_path=fixtures.config.dsk_token_path,
        token=fixtures.config.upload_token,
        check_output=False,
    )


@then("I get an error message that the metadata has already been processed")
def check_ingest_output(ingest_output: subprocess.CompletedProcess):
    assert "ERROR" in ingest_output.stderr
    assert "409 Conflict" in ingest_output.stderr.strip()
    assert "Metadata has already been processed." in ingest_output.stdout.strip()
