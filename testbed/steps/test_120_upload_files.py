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

"""Step definitions for uploading and ingesting files with the datasteward-kit"""

import json
import os
import shutil
import subprocess
from pathlib import Path

from fixtures.config import Config, S3StorageConfig
from fixtures.file import FileBatch, FileObject, subset_file_batch_by_scope
from fixtures.utils import temporary_file
from ghga_datasteward_kit.file_ingest import IngestConfig, alias_to_accession
from metldata.submission_registry.submission_store import SubmissionStore

from steps.utils import get_secret_ids, ingest_config_as_file, upload_config_as_file

from .conftest import JointFixture, given, parse, scenarios, then, when

scenarios("../features/120_upload_files.feature")


def call_data_steward_kit_upload(
    file_alias: str,
    file_path: str,
    config: Config,
    file_metadata_dir: Path,
    token_path: Path,
    token: str,
    storage_config: S3StorageConfig,
):
    """Call DSKit upload command to upload a file"""
    upload_config_path = upload_config_as_file(
        config=config,
        file_metadata_dir=file_metadata_dir,
        storage_config=storage_config,
    )

    with temporary_file(token_path, token) as _:
        completed_upload = subprocess.run(  # nosec B607, B603
            [
                "ghga-datasteward-kit",
                "files",
                "upload",
                "--alias",
                file_alias,
                "--input-path",
                file_path,
                "--config-path",
                upload_config_path,
            ],
            capture_output=True,
            check=False,
            encoding="utf-8",
            text=True,
            timeout=60,
        )

    if completed_upload.stdout:
        print(completed_upload.stdout)
    if "ERROR" in completed_upload.stderr or completed_upload.returncode:
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
    storage_config: S3StorageConfig,
):
    """Call DSKit batch-upload command to upload listed files in TSV file"""
    upload_config_path = upload_config_as_file(
        config=config,
        file_metadata_dir=file_metadata_dir,
        storage_config=storage_config,
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

    if completed_upload.stdout:
        print(completed_upload.stdout)
    if "ERROR" in completed_upload.stderr or completed_upload.returncode:
        print(completed_upload.stderr)

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

    if "Successfully" not in completed_ingest.stdout:
        print(completed_ingest.stdout)
    if "ERROR" in completed_ingest.stderr or completed_ingest.returncode:
        print(completed_ingest.stderr)

    assert (
        completed_ingest.stdout.strip()
        == "Successfully sent all file upload metadata for ingest."
    )
    assert not "ERROR" in completed_ingest.stderr
    assert not completed_ingest.returncode


@given("the staging buckets are empty")
def staging_buckets_are_empty(fixtures: JointFixture):
    for storage_name in ["primary", "secondary"]:
        storage_config = fixtures.s3.get_storage_config(storage_name)
        fixtures.s3.empty_buckets(
            storages=storage_config,
            buckets=storage_config.buckets.staging,
        )


@given("no file metadata exists")
def local_metadata_empty(fixtures: JointFixture):
    file_metadata_dir = fixtures.dsk.config.file_metadata_dir
    if os.path.exists(file_metadata_dir):
        shutil.rmtree(file_metadata_dir)


@when(
    parse(
        'the files of dataset "{dataset_alias}" are uploaded to "{storage_name}" storage individually'
    ),
    target_fixture="file_objects",
)
def upload_files_individually(
    fixtures: JointFixture,
    file_fixture: dict[str, FileBatch],
    dataset_alias: str,
    storage_name: str,
) -> list[FileObject]:
    file_metadata_dir = fixtures.dsk.config.file_metadata_dir
    file_metadata_dir.mkdir(exist_ok=True)

    assert file_fixture.keys() == {"DS_A", "DS_B"}
    assert dataset_alias in file_fixture, f"Dataset {dataset_alias} not found"

    storage_config = fixtures.s3.get_storage_config(storage_name)
    tsv_file = file_fixture[dataset_alias].tsv_file
    with open(tsv_file, encoding="utf-8") as fh:
        for file_object in fh:
            file_path, file_alias = file_object.strip().split("\t")

            call_data_steward_kit_upload(
                file_alias=file_alias,
                file_path=file_path,
                config=fixtures.config,
                file_metadata_dir=file_metadata_dir,
                token_path=fixtures.config.dsk_token_path,
                token=fixtures.config.upload_token,
                storage_config=storage_config,
            )
    return file_fixture[dataset_alias].file_objects


@when(
    parse(
        '"{file_scope}" files of dataset "{dataset_alias}" are uploaded to "{storage_name}" storage in batch'
    ),
    target_fixture="file_objects",
)
def upload_files_as_batch(
    fixtures: JointFixture,
    file_fixture: dict[str, FileBatch],
    file_scope: str,
    dataset_alias: str,
    storage_name: str,
) -> list[FileObject]:
    file_metadata_dir = fixtures.dsk.config.file_metadata_dir
    file_metadata_dir.mkdir(exist_ok=True)

    assert file_fixture.keys() == {"DS_A", "DS_B"}
    assert dataset_alias in file_fixture, f"Dataset {dataset_alias} not found"

    file_batch = file_fixture[dataset_alias]
    if file_scope != "all":
        file_batch = subset_file_batch_by_scope(file_fixture[dataset_alias], file_scope)

    storage_config = fixtures.s3.get_storage_config(storage_name)
    tsv_file = file_batch.tsv_file
    call_data_steward_kit_batch_upload(
        batch_files_tsv=tsv_file,
        config=fixtures.config,
        file_metadata_dir=file_metadata_dir,
        token_path=fixtures.config.dsk_token_path,
        token=fixtures.config.upload_token,
        storage_config=storage_config,
    )
    return file_batch.file_objects


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


@then(
    parse('the uploaded files exist in the staging bucket of "{storage_name}" storage')
)
def check_uploaded_files_in_storage(
    fixtures: JointFixture, uploaded_file_uuids: set[str], storage_name: str
):
    """Check that the uploaded files exist in the given bucket."""
    storage_config = fixtures.s3.get_storage_config(storage_name)
    bucket_id = storage_config.buckets.staging
    storage_config = fixtures.s3.get_storage_config(storage_name)
    for object_id in uploaded_file_uuids:
        assert fixtures.s3.does_object_exist(
            storage_alias=storage_config.storage_alias,
            bucket=bucket_id,
            object_id=object_id,
        ), f"{object_id} does not exist in the staging bucket"


@when(
    parse('the file metadata uploaded to "{storage_name}" storage is ingested'),
    target_fixture="ingest_config",
)
def ingest_file_metadata(fixtures: JointFixture, storage_name: str) -> IngestConfig:
    storage_config = fixtures.s3.get_storage_config(storage_name)
    ingest_config = IngestConfig(
        file_ingest_baseurl=fixtures.config.fis_url,
        file_ingest_pubkey=fixtures.config.fis_pubkey,
        input_dir=fixtures.dsk.config.file_metadata_dir,
        submission_store_dir=fixtures.dsk.config.submission_store,
        map_files_fields=list(fixtures.dsk.config.metadata_file_fields),
        selected_storage_alias=storage_config.storage_alias,
        fallback_bucket_id=storage_config.buckets.staging,
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
    file_information = fixtures.state.get_state("all file information") or {}
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
            file_metadata = json.loads(metadata_file_path.read_text())
            # Store basic file information for later use
            file_information[accession] = {
                "size": file_metadata["Unencrypted file size"],
                "sha256_hash": file_metadata["Unencrypted file checksum"],
                "storage_alias": file_metadata["Storage alias"],
            }
    assert accessions
    fixtures.state.set_state("all file information", file_information)

    documents = fixtures.mongo.wait_for_documents(
        db_name=fixtures.config.ifrs_db_name,
        collection_name=fixtures.config.ifrs_metadata_collection,
        query={"_id": {"$in": list(accessions)}},
        number=len(accessions),
    )
    assert documents
    return {document["object_id"] for document in documents}


@then(parse("the file encryption secret is saved in the vault"))
def check_secrets_in_vault(fixtures: JointFixture, file_objects: list[FileObject]):
    secret_ids = get_secret_ids(fixtures.dsk.config.file_metadata_dir, file_objects)
    if not fixtures.config.vault_token:
        return  # skip test if no vault token is provided
    vault_keys = fixtures.vault.keys
    for secret_id in secret_ids:
        assert secret_id in vault_keys


@then(
    parse(
        'the ingested files exist in the permanent bucket of "{storage_name}" storage'
    )
)
def check_ingested_files_in_storage(
    fixtures: JointFixture, object_ids: set[str], storage_name: str
):
    """Check that the ingested files exist in the permanent bucket."""
    storage_config = fixtures.s3.get_storage_config(storage_name)
    for object_id in object_ids:
        assert fixtures.s3.does_object_exist(
            storage_alias=storage_config.storage_alias,
            bucket=storage_config.buckets.permanent,
            object_id=object_id,
        ), f"{object_id} does not exist in the permanent bucket"
