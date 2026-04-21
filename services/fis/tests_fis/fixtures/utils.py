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

"""Utils for Fixture handling"""

from pathlib import Path
from uuid import uuid4

from hexkit.utils import now_utc_ms_prec

from fis.core.models import FileUnderInterrogation

BASE_DIR = Path(__file__).parent.resolve()


def create_file_under_interrogation(storage_alias: str):
    """Generate some dummy data for the specified storage_alias"""
    file = FileUnderInterrogation(
        id=uuid4(),
        storage_alias=storage_alias,
        bucket_id="inbox1",
        object_id=uuid4(),
        decrypted_sha256="38d141b35057bbb691b9756c20a6c31a0ab0bbf2076538a7fb6d9ee8835096d7",
        decrypted_size=123456789,
        encrypted_size=123466789,
        part_size=12345,
        state="inbox",
        state_updated=now_utc_ms_prec(),
        can_remove=False,
    )
    return file
