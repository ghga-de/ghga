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

"""Step definitions for uploading and ingesting files with the datasteward-kit"""

import json
import os
import shutil
import subprocess
from pathlib import Path

from fixtures.config import Config
from fixtures.file import FileBatch, FileObject
from fixtures.utils import temporary_file
from ghga_datasteward_kit.file_ingest import IngestConfig, alias_to_accession
from metldata.submission_registry.submission_store import SubmissionStore
from pytest import fixture

from steps.utils import get_secret_ids, ingest_config_as_file, upload_config_as_file

from .conftest import JointFixture, async_step, given, parse, scenarios, then, when

scenarios("../features/12_upload_files.feature")


def call_data_steward_kit_upload(
    file_object: FileObject,
    config: Config,
    file_metadata_dir: Path,
    token_path: Path,
    token: str,
):
    """Call DSKit upload command to upload a file"""
    upload_config_path = upload_config_as_file(
        config=config,
        file_metadata_dir=file_metadata_dir,
    )

    with temporary_file(token_path, token) as _:
        completed_upload = subprocess.run(  # nosec B607, B603
            [
                "ghga-datasteward-kit",
                "files",
                "upload",
                "--alias",
                file_object.object_id,
                "--input-path",
                str(file_object.file_path),
                "--config-path",
                upload_config_path,
            ],
            capture_output=True,
            check=False,
            encoding="utf-8",
            text=True,
            timeout=60,
        )

    print("STDERR")
    print(completed_upload.stderr)

    assert not completed_upload.stdout
    assert "ERROR" not in completed_upload.stderr
    assert not completed_upload.returncode


def call_data_steward_kit_batch_upload(
    batch_files_tsv: Path,
    config: Config,
    file_metadata_dir: Path,
    token_path: Path,
    token: str,
):
    """Call DSKit batch-upload command to upload listed files in TSV file"""
    upload_config_path = upload_config_as_file(
        config=config, file_metadata_dir=file_metadata_dir
    )

    with temporary_file(token_path, token) as _:
        completed_upload = subprocess.run(  # nosec B607, B603
            [
                "ghga-datasteward-kit",
                "files",
                "batch-upload",
                "--tsv",
                str(batch_files_tsv),
                "--config-path",
                upload_config_path,
                "--parallel-processes",
                "2",
            ],
            capture_output=True,
            check=False,
            encoding="utf-8",
            text=True,
            timeout=180,
        )

    assert not completed_upload.stdout
    assert "ERROR" not in completed_upload.stderr
    assert not completed_upload.returncode


def call_data_steward_kit_ingest(
    ingest_config_path: str, token_path: Path, token: str
) -> None:
    """Call DSKit file_ingest command to ingest file"""
    with temporary_file(token_path, token) as _:
        completed_ingest = subprocess.run(  # nosec B607, B603
            [
                "ghga-datasteward-kit",
                "files",
                "ingest-upload-metadata",
                "--config-path",
                ingest_config_path,
            ],
            capture_output=True,
            check=False,
            encoding="utf-8",
            text=True,
            timeout=10 * 60,
        )

    assert (
        completed_ingest.stdout.strip()
        == "Successfully sent all file upload metadata for ingest."
    )
    assert not completed_ingest.stderr
    assert not completed_ingest.returncode


@given("the staging bucket is empty")
@async_step
async def staging_bucket_is_empty(fixtures: JointFixture):
    config = fixtures.config
    await fixtures.s3.empty_given_buckets([config.staging_bucket])


@given("no file metadata exists")
def local_metadata_empty(fixtures: JointFixture):
    file_metadata_dir = fixtures.dsk.config.file_metadata_dir
    if os.path.exists(file_metadata_dir):
        shutil.rmtree(file_metadata_dir)


@when(
    parse("the files for the minimal metadata are uploaded individually"),
    target_fixture="file_objects",
)
def upload_files_individually(
    fixtures: JointFixture, file_fixture: list[FileObject]
) -> list[FileObject]:
    file_metadata_dir = fixtures.dsk.config.file_metadata_dir
    file_metadata_dir.mkdir(exist_ok=True)

    for file_object in file_fixture:
        call_data_steward_kit_upload(
            file_object=file_object,
            config=fixtures.config,
            file_metadata_dir=file_metadata_dir,
            token_path=fixtures.config.dsk_token_path,
            token=fixtures.config.upload_token,
        )
    return file_fixture


@when(
    "the files for the complete metadata are uploaded as a batch",
    target_fixture="file_objects",
)
def upload_files_as_batch(
    fixtures: JointFixture, batch_file_fixture: FileBatch
) -> list[FileObject]:
    file_metadata_dir = fixtures.dsk.config.file_metadata_dir
    file_metadata_dir.mkdir(exist_ok=True)

    tsv_file = batch_file_fixture.tsv_file
    call_data_steward_kit_batch_upload(
        batch_files_tsv=tsv_file,
        config=fixtures.config,
        file_metadata_dir=file_metadata_dir,
        token_path=fixtures.config.dsk_token_path,
        token=fixtures.config.upload_token,
    )
    return batch_file_fixture.file_objects


@then(
    "the file metadata for each uploaded file exists",
    target_fixture="uploaded_file_uuids",
)
def metadata_files_exist(
    fixtures: JointFixture, file_objects: list[FileObject]
) -> set[str]:
    """Check that the file metadata exists and return the UUIDs."""
    file_metadata_dir = fixtures.dsk.config.file_metadata_dir
    file_uuids = set()
    for file_object in file_objects:
        metadata_file_path = file_metadata_dir / f"{file_object.object_id}.json"
        assert metadata_file_path.exists()
        file_uuid = json.loads(metadata_file_path.read_text())["File UUID"]
        file_uuids.add(file_uuid)
    return file_uuids


@then(parse("the uploaded files exist in the staging bucket"))
@async_step
async def check_uploaded_files_in_storage(
    fixtures: JointFixture, uploaded_file_uuids: set[str]
):
    """Check that the uploaded files exist in the given bucket."""
    if fixtures.config.use_api_gateway:
        # black-box testing: cannot check staging bucket
        return
    bucket_id = fixtures.config.staging_bucket
    for object_id in uploaded_file_uuids:
        assert await fixtures.s3.storage.does_object_exist(
            bucket_id=bucket_id, object_id=object_id
        ), f"{object_id} does not exist in the staging bucket"


@when("the file metadata is ingested", target_fixture="ingest_config")
def ingest_file_metadata(fixtures: JointFixture) -> IngestConfig:
    ingest_config = IngestConfig(
        file_ingest_baseurl=fixtures.config.fis_url,
        file_ingest_pubkey=fixtures.config.fis_pubkey,
        input_dir=fixtures.dsk.config.file_metadata_dir,
        submission_store_dir=fixtures.dsk.config.submission_store,
        map_files_fields=list(fixtures.dsk.config.metadata_file_fields),
    )

    ingest_config_path = ingest_config_as_file(config=ingest_config)

    call_data_steward_kit_ingest(
        ingest_config_path=ingest_config_path,
        token_path=fixtures.config.dsk_token_path,
        token=fixtures.config.upload_token,
    )

    return ingest_config


@then(
    "the file metadata is stored in the internal file registry",
    target_fixture="object_ids",
)
def check_metadata_documents(
    fixtures: JointFixture, ingest_config: IngestConfig
) -> set[str]:
    accessions: set[str] = set()
    file_metadata_dir = fixtures.dsk.config.file_metadata_dir
    for metadata_file_path in file_metadata_dir.iterdir():
        if metadata_file_path.suffix == ".json":
            alias = metadata_file_path.stem
            accession = alias_to_accession(
                alias=alias,
                map_fields=ingest_config.map_files_fields,
                submission_store=SubmissionStore(config=ingest_config),
            )
            accessions.add(accession)

    assert accessions

    if fixtures.config.use_api_gateway:
        # if we use the API gateway, we cannot access the database directly
        # and therefore just return the accessions
        return accessions

    documents = fixtures.mongo.wait_for_documents(
        db_name=fixtures.config.ifrs_db_name,
        collection_name=fixtures.config.ifrs_metadata_collection,
        mapping={"_id": {"$in": list(accessions)}},
        number=len(accessions),
    )
    assert documents
    return {document["object_id"] for document in documents}


@then(parse("the file encryption secret is saved in the vault"))
def check_secrets_in_vault(fixtures: JointFixture, file_objects: list[FileObject]):
    secret_ids = get_secret_ids(fixtures.dsk.config.file_metadata_dir, file_objects)
    for secret_id in secret_ids:
        assert bool(secret_id in fixtures.vault.keys) == True


@then(parse("the ingested files exist in the permanent bucket"))
@async_step
async def check_ingested_files_in_storage(fixtures: JointFixture, object_ids: set[str]):
    """Check that the ingested files exist in the permanent bucket."""
    if fixtures.config.use_api_gateway:
        # black-box testing: cannot check permanent bucket
        return
    for object_id in object_ids:
        assert await fixtures.s3.storage.does_object_exist(
            bucket_id=fixtures.config.permanent_bucket, object_id=object_id
        ), f"{object_id} does not exist in the permanent bucket"
