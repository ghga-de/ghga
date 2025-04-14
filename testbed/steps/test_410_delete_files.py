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

"""Step definitions for deleting datasets"""

from time import sleep

import hvac.exceptions

from .conftest import (
    Config,
    HttpClient,
    JointFixture,
    MongoFixture,
    Response,
    StateStorage,
    parse,
    scenarios,
    then,
    when,
)

scenarios("../features/410_delete_files.feature")

TIMEOUT = 5
INTERVAL = 0.1


@when("the files of the complete datasets are requested to be deleted")
def delete_files_of_complete_datasets(http: HttpClient, fixtures: JointFixture):
    auth_headers = {"Authorization": f"Bearer {fixtures.config.purge_controller_token}"}
    file_information = fixtures.state.get_state("all file information") or {}
    for file_id in file_information:
        url = f"{fixtures.config.pcs_url}/files/{file_id}"
        response = http.delete(url, headers=auth_headers)
        assert response.status_code == 202, (
            f"Failed to delete file {file_id}: {response.text}"
        )

        # Wait for the file deletion request to be stored
        document = fixtures.mongo.wait_for_document(
            fixtures.config.pcs_db_name,
            fixtures.config.pcs_file_deletion_event_collection,
            query={"key": file_id},
            timeout=TIMEOUT,
        )
        assert document


@then("the file metadata is removed from the file backend")
def check_services_for_deleted_files(fixtures: JointFixture):
    file_information = fixtures.state.get_state("all file information") or {}
    accessions = list(file_information.keys())
    config = fixtures.config

    services = [
        (config.dins_db_name, config.dins_metadata_collection),  # dataset information
        (
            config.ifrs_db_name,
            config.ifrs_metadata_collection,
        ),  # internal file registry
        (config.dcs_db_name, config.dcs_objects_collection),  # download controller
    ]

    for service in services:
        documents = fixtures.mongo.wait_for_documents(
            db_name=service[0],
            collection_name=service[1],
            query={"_id": {"$in": accessions}},
            number=len(accessions),
            timeout=TIMEOUT,
        )
        assert not documents, (
            f"File metadata still exist in the {service[0]}.{service[1]}: {documents}"
        )


@then("the deleted files do not exist in the storage")
def check_storage_for_deleted_files(fixtures: JointFixture):
    timeout = TIMEOUT
    interval = INTERVAL
    for storage_name in ["primary", "secondary"]:
        storage_config = fixtures.s3.get_storage_config(storage_name)
        buckets = [storage_config.buckets.permanent, storage_config.buckets.outbox]
        for bucket in buckets:
            slept: float = 0
            while slept < timeout:
                file_objects = fixtures.s3.list_objects(
                    storage_alias=storage_config.storage_alias, bucket=bucket
                )
                if not file_objects:
                    return
                sleep(interval)
                slept += interval
            assert False, f"Files still exist in storage: {storage_name}.{bucket}"


@then("the file encryption secrets are removed from the vault")
def check_secrets_in_vault(fixtures: JointFixture):
    vault_keys = fixtures.vault.keys()
    assert not vault_keys, f"File encryption secrets still exist in Vault: {vault_keys}"
