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

"""Test the creation of dataclasses and DTOs"""

from datetime import datetime, timezone

from wps.core.models import WorkOrderToken, WorkPackage, WorkType


def test_work_order_token():
    """Test the instantiating a work order token object."""
    token = WorkOrderToken(
        type=WorkType.DOWNLOAD,
        file_id="some-file-id",
        user_id="some-user-id",
        public_key="some-public-key",
        full_user_name="Dr. John Doe",
        email="john@home.org",
    )
    assert token.full_user_name == "Dr. John Doe"


def test_work_package():
    """Test instantiating a work package DTO."""
    package = WorkPackage(
        id="some-workpackage-id",
        user_id="some-user-id",
        dataset_id="some-dataset-id",
        type=WorkType.DOWNLOAD,
        file_ids=["some-file-id", "another-file-id"],
        user_public_crypt4gh_key="c29tZS1wdWJsaWMta2V5",
        full_user_name="Dr. John Doe",
        email="john@home.org",
        token_hash="308eda9daf26b7446b284449a5895ab9a04ff30c129d4454e471cfb81bf5557d",
        file_extensions={"some-file-id": ".sam", "another-file-id": ".bam"},
        created=datetime(2022, 2, 2, 2, tzinfo=timezone.utc),
        expires=datetime(2022, 2, 2, 3, tzinfo=timezone.utc),
    )
    assert package.id == "some-workpackage-id"
    assert package.full_user_name == "Dr. John Doe"
    assert package.file_extensions["another-file-id"] == ".bam"
    assert (package.expires - package.created).seconds == 60 * 60
