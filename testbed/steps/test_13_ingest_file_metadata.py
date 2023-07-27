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


""" Step definitions for file ingest """

import subprocess

from ghga_datasteward_kit.file_ingest import IngestConfig, alias_to_accession
from metldata.submission_registry.submission_store import SubmissionStore

from steps.utils import ingest_config_as_file, temporary_file

from .conftest import (
    DSK_TOKEN_PATH,
    IFRS_DB_NAME,
    IFRS_METADATA_COLLECTION,
    JointFixture,
    async_step,
    get_state,
    scenarios,
    then,
    when,
)

scenarios("../features/13_ingest_file_metadata.feature")


def call_data_steward_kit_ingest(ingest_config_path: str, token):
    """Call DSKit file_ingest command to ingest file"""

    with temporary_file(DSK_TOKEN_PATH, token) as _:
        completed_ingest = subprocess.run(  # nosec B607, B603
            [
                "ghga-datasteward-kit",
                "files",
                "ingest-upload-metadata",
                "--config-path",
                ingest_config_path,
            ],
            capture_output=True,
            check=True,
            encoding="utf-8",
            text=True,
            timeout=10 * 60,
        )

        assert not completed_ingest.returncode
        assert "ERROR" not in completed_ingest.stderr


@when("file metadata is ingested", target_fixture="ingest_config")
def ingest_file_metadata(fixtures: JointFixture):
    ingest_config = IngestConfig(
        file_ingest_url=fixtures.config.file_ingest_url,
        file_ingest_pubkey=fixtures.config.file_ingest_pubkey,
        input_dir=fixtures.dsk.config.file_metadata_dir,
        submission_store_dir=fixtures.dsk.config.submission_store,
        map_files_fields=fixtures.dsk.config.metadata_file_fields,
    )

    ingest_config_path = ingest_config_as_file(config=ingest_config)

    call_data_steward_kit_ingest(
        ingest_config_path=ingest_config_path,
        token=fixtures.auth.read_simple_token(),
    )

    return ingest_config


@then("we have the file accessions", target_fixture="accessions")
def check_file_accessions_exist(ingest_config, fixtures: JointFixture):
    file_aliases = get_state("we have file aliases", fixtures.mongo)
    file_accessions = []
    for alias in file_aliases:
        accession = alias_to_accession(
            alias=alias,
            map_fields=ingest_config.map_files_fields,
            submission_store=SubmissionStore(config=ingest_config),
        )
        assert accession.startswith("GHGAF")
        file_accessions.append(accession)
    return file_accessions


@then("file metadata exist in the service", target_fixture="object_ids")
def check_metadata_documents(accessions: list[str], fixtures: JointFixture):
    documents = fixtures.mongo.wait_for_documents(
        db_name=IFRS_DB_NAME,
        collection_name=IFRS_METADATA_COLLECTION,
        mapping={"_id": {"$in": accessions}},
        number=2,
    )
    assert documents
    return [d["object_id"] for d in documents]


@then("files exist in permanent bucket")
@async_step
async def check_files_in_storage(fixtures: JointFixture, object_ids: list[str]):
    """Check object exist with async fixture"""
    for object_id in object_ids:
        assert await fixtures.s3.storage.does_object_exist(
            bucket_id=fixtures.config.permanent_bucket, object_id=object_id
        )
    return True
