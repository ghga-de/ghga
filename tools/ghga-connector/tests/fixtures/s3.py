# Copyright 2021 - 2022 Universität Tübingen, DKFZ and EMBL
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

"""Fixtures for testing the storage DAO"""

from typing import List

from ghga_service_chassis_lib.object_storage_dao_testing import ObjectFixture
from ghga_service_chassis_lib.s3_testing import s3_fixture_factory

from . import state

existing_buckets: List[str] = ["inbox", "outbox"]
existing_objects: List[ObjectFixture] = []

for file in state.FILES.values():
    if file.populate_storage:
        for storage_object in file.storage_objects:
            if storage_object.bucket_id not in existing_buckets:
                existing_buckets.append(storage_object.bucket_id)
            existing_objects.append(storage_object)

s3_fixture = s3_fixture_factory(
    existing_buckets=existing_buckets,
    existing_objects=existing_objects,
)
