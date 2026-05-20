# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Test data for the V3 migration"""

from typing import Any
from uuid import UUID

from hexkit.utils import now_utc_ms_prec

TEST_DATETIME = now_utc_ms_prec()

OLD_DRS_OBJECTS: list[dict[str, Any]] = [
    {
        "_id": "GHGAF06564866469116",
        "decryption_secret_id": "bec11335-f86b-4272-9dbb-a91f4aeca316",
        "decrypted_sha256": "fc4dbaa4e65acd61426b5029bada0077a71dd5f1fddb3fe6acad190ab0a4903a",
        "decrypted_size": 1084227584,
        "encrypted_size": 1084690816,
        "creation_date": TEST_DATETIME,
        "s3_endpoint_alias": "HD01",
        "object_id": UUID("0331bf89-a880-4b1e-aa00-5ea92b7ded5a"),
        "last_accessed": TEST_DATETIME,
    },
    {
        "_id": "GHGAF65447737384561",
        "decryption_secret_id": "d21d3d9a-19f6-4fc2-a763-7cee9a5aa89f",
        "decrypted_sha256": "5c767e0fd996fbc31eddeaf140f14e247e080e12617856d23de5147a5e57ccf1",
        "decrypted_size": 1352663040,
        "encrypted_size": 1353240960,
        "creation_date": TEST_DATETIME,
        "s3_endpoint_alias": "HD01",
        "object_id": UUID("6ed5c73b-41fe-4cc5-bb3a-068da4c3ab97"),
        "last_accessed": TEST_DATETIME,
    },
]
EXPECTED_MIGRATED_DRS_OBJECTS: list[dict[str, Any]] = [
    {
        "_id": UUID("34b9b256-9efe-45bd-a16e-3f50ad12bc73"),
        "secret_id": "bec11335-f86b-4272-9dbb-a91f4aeca316",
        "decrypted_sha256": "fc4dbaa4e65acd61426b5029bada0077a71dd5f1fddb3fe6acad190ab0a4903a",
        "decrypted_size": 1084227584,
        "encrypted_size": 1084690816,
        "creation_date": TEST_DATETIME,
        "storage_alias": "HD01",
        "object_id": UUID("0331bf89-a880-4b1e-aa00-5ea92b7ded5a"),
        "last_accessed": TEST_DATETIME,
    },
    {
        "_id": UUID("752162f9-7ea7-4d8e-a2c8-99666d2f6b51"),
        "secret_id": "d21d3d9a-19f6-4fc2-a763-7cee9a5aa89f",
        "decrypted_sha256": "5c767e0fd996fbc31eddeaf140f14e247e080e12617856d23de5147a5e57ccf1",
        "decrypted_size": 1352663040,
        "encrypted_size": 1353240960,
        "creation_date": TEST_DATETIME,
        "storage_alias": "HD01",
        "object_id": UUID("6ed5c73b-41fe-4cc5-bb3a-068da4c3ab97"),
        "last_accessed": TEST_DATETIME,
    },
]

OLD_PERSISTED_EVENTS: list[dict[str, Any]] = [
    {  # FileDownloadServed
        "_id": "staging-downloads:GHGAF62145458747015",
        "topic": "staging-downloads",
        "type_": "drs_object_registered",
        "payload": {
            "upload_date": TEST_DATETIME,
            "file_id": "GHGAF62145458747015",
            "decrypted_sha256": "7683b3edb54e8705bbdba7519fdc7048b995644159507fe837f5ea2d0377dbde",
            "drs_uri": "drs://someurl/GHGAF62145458747015",
        },
        "key": "GHGAF62145458747015",
        "headers": {},
        "correlation_id": UUID("2111c101-cc1b-43e9-8500-fc9b2799602d"),
        "created": TEST_DATETIME,
        "published": True,
        "event_id": UUID("5b04fe60-1436-46ca-aeec-a7fc6aaaf33f"),
    },
    {  # FileRegisteredForDownload with old str-value target_object_id
        "_id": "staging-downloads:GHGAF91819066635026",
        "topic": "staging-downloads",
        "type_": "drs_object_served",
        "payload": {
            "file_id": "GHGAF91819066635026",
            "target_object_id": "83393cc5-fec9-4a2c-a908-41a3b4be2a1a",
            "target_bucket_id": "outbox-staging",
            "s3_endpoint_alias": "B01",
            "decrypted_sha256": "e5b844cc57f57094ea4585e235f36c78c1cd222262bb89d53c94dcb4d6b3e55d",
            "context": "unknown",
        },
        "key": "GHGAF91819066635026",
        "headers": {},
        "correlation_id": UUID("ec0411cb-1328-4c00-bc53-64b66aba8aaf"),
        "created": TEST_DATETIME,
        "published": True,
        "event_id": UUID("a5343581-25c8-45d2-ac53-f850c02bcea9"),
    },
    {  # FileRegisteredForDownload with newer UUID-value target_object_id
        "_id": "staging-downloads:GHGAF92819066635026",
        "topic": "staging-downloads",
        "type_": "drs_object_served",
        "payload": {
            "file_id": "GHGAF92819066635026",
            "target_object_id": UUID("a6370254-3555-4f77-b939-572452770aa5"),
            "target_bucket_id": "outbox-staging",
            "s3_endpoint_alias": "B01",
            "decrypted_sha256": "e5b844cc57f57094ea4585e235f36c78c1cd222262bb89d53c94dcb4d6b3e55d",
            "context": "unknown",
        },
        "key": "GHGAF92819066635026",
        "headers": {},
        "correlation_id": UUID("7a0f695a-f91c-4acd-91c3-ea2a52cfceff"),
        "created": TEST_DATETIME,
        "published": True,
        "event_id": UUID("61788c24-de12-44a7-8367-60398cdd907b"),
    },
]

EXPECTED_MIGRATED_PERSISTED_EVENTS: list[dict[str, Any]] = [
    {
        "_id": "staging-downloads:1805247b-4276-4a66-a287-57897f6bfcea",
        "topic": "staging-downloads",
        "type_": "drs_object_registered",
        "payload": {
            "archive_date": TEST_DATETIME,
            "file_id": UUID("1805247b-4276-4a66-a287-57897f6bfcea"),
            "decrypted_sha256": "7683b3edb54e8705bbdba7519fdc7048b995644159507fe837f5ea2d0377dbde",
        },
        "key": "1805247b-4276-4a66-a287-57897f6bfcea",
        "headers": {},
        "correlation_id": UUID("2111c101-cc1b-43e9-8500-fc9b2799602d"),
        "created": TEST_DATETIME,
        "published": False,
        "event_id": UUID("5b04fe60-1436-46ca-aeec-a7fc6aaaf33f"),
    },
    {
        "_id": "staging-downloads:958240ef-a863-4908-a141-b95f6c43c67b",
        "topic": "staging-downloads",
        "type_": "drs_object_served",
        "payload": {
            "file_id": UUID("958240ef-a863-4908-a141-b95f6c43c67b"),
            "target_object_id": UUID("83393cc5-fec9-4a2c-a908-41a3b4be2a1a"),
            "target_bucket_id": "outbox-staging",
            "storage_alias": "B01",
            "decrypted_sha256": "e5b844cc57f57094ea4585e235f36c78c1cd222262bb89d53c94dcb4d6b3e55d",
            "context": "unknown",
        },
        "key": "958240ef-a863-4908-a141-b95f6c43c67b",
        "headers": {},
        "correlation_id": UUID("ec0411cb-1328-4c00-bc53-64b66aba8aaf"),
        "created": TEST_DATETIME,
        "published": False,
        "event_id": UUID("a5343581-25c8-45d2-ac53-f850c02bcea9"),
    },
    {
        "_id": "staging-downloads:bb4262e4-1d12-4313-ac21-c2b16fb5e7aa",
        "topic": "staging-downloads",
        "type_": "drs_object_served",
        "payload": {
            "file_id": UUID("bb4262e4-1d12-4313-ac21-c2b16fb5e7aa"),
            "target_object_id": UUID("a6370254-3555-4f77-b939-572452770aa5"),
            "target_bucket_id": "outbox-staging",
            "storage_alias": "B01",
            "decrypted_sha256": "e5b844cc57f57094ea4585e235f36c78c1cd222262bb89d53c94dcb4d6b3e55d",
            "context": "unknown",
        },
        "key": "bb4262e4-1d12-4313-ac21-c2b16fb5e7aa",
        "headers": {},
        "correlation_id": UUID("7a0f695a-f91c-4acd-91c3-ea2a52cfceff"),
        "created": TEST_DATETIME,
        "published": False,
        "event_id": UUID("61788c24-de12-44a7-8367-60398cdd907b"),
    },
]
