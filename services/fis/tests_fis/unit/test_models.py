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

"""Unit tests for models"""

from uuid import uuid4

import pytest
from hexkit.utils import now_utc_ms_prec
from pydantic import SecretBytes, ValidationError

from fis.core.models import InterrogationReportWithSecret


def test_interrogation_report_validator():
    """Test the validator on the InterrogationReport model"""
    file_id = uuid4()
    storage_alias = "test-alias"
    bucket_id = "interrogation1"
    interrogated_at = now_utc_ms_prec()

    # Valid case: passed=True with all required fields
    valid_success = InterrogationReportWithSecret(
        file_id=file_id,
        storage_alias=storage_alias,
        bucket_id=bucket_id,
        object_id=uuid4(),
        interrogated_at=interrogated_at,
        passed=True,
        secret=SecretBytes(b"encrypted_secret"),
        encrypted_parts_md5=["abc123"],
        encrypted_parts_sha256=["def456"],
        encrypted_size=1234,
    )
    assert valid_success.passed is True

    # Valid case: passed=False with reason
    valid_failure = InterrogationReportWithSecret(
        file_id=file_id,
        storage_alias=storage_alias,
        interrogated_at=interrogated_at,
        passed=False,
        reason="Checksum mismatch",
    )
    assert valid_failure.passed is False

    # Invalid: passed=True but bucket_id is None
    with pytest.raises(ValidationError, match="bucket_id must not be None"):
        InterrogationReportWithSecret(
            file_id=file_id,
            storage_alias=storage_alias,
            interrogated_at=interrogated_at,
            passed=True,
            secret=SecretBytes(b"encrypted_secret"),
            encrypted_parts_md5=["abc123"],
            encrypted_parts_sha256=["def456"],
        )

    # Invalid: passed=True but encrypted_parts_md5 is None
    with pytest.raises(ValidationError, match="encrypted_parts_md5 must not be None"):
        InterrogationReportWithSecret(
            file_id=file_id,
            storage_alias=storage_alias,
            bucket_id=bucket_id,
            object_id=uuid4(),
            interrogated_at=interrogated_at,
            passed=True,
            secret=SecretBytes(b"encrypted_secret"),
            encrypted_parts_md5=None,
            encrypted_parts_sha256=["def456"],
        )

    # Invalid: passed=True but encrypted_parts_sha256 is None
    with pytest.raises(
        ValidationError, match="encrypted_parts_sha256 must not be None"
    ):
        InterrogationReportWithSecret(
            file_id=file_id,
            storage_alias=storage_alias,
            bucket_id=bucket_id,
            object_id=uuid4(),
            interrogated_at=interrogated_at,
            passed=True,
            secret=SecretBytes(b"encrypted_secret"),
            encrypted_parts_md5=["abc123"],
            encrypted_parts_sha256=None,
        )

    # Invalid: passed=True but secret is None
    with pytest.raises(ValidationError, match="secret must not be None"):
        InterrogationReportWithSecret(
            file_id=file_id,
            storage_alias=storage_alias,
            bucket_id=bucket_id,
            object_id=uuid4(),
            interrogated_at=interrogated_at,
            passed=True,
            secret=None,
            encrypted_parts_md5=["abc123"],
            encrypted_parts_sha256=["def456"],
        )

    # Invalid: passed=False but reason is None
    with pytest.raises(ValidationError, match="reason must not be None"):
        InterrogationReportWithSecret(
            file_id=file_id,
            storage_alias=storage_alias,
            interrogated_at=interrogated_at,
            passed=False,
            reason=None,
        )
