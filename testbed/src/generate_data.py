# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Functionality dealing with data generation upload/download"""

import base64
import hashlib
from tempfile import NamedTemporaryFile

import crypt4gh.header
import crypt4gh.keys
import crypt4gh.lib
from ghga_service_commons.utils.temp_files import big_temp_file

from src.config import Config


def generate_file(config: Config):
    """Generate encrypted test file, return both unencrypted and encrypted data as bytes"""
    with big_temp_file(size=config.file_size) as random_data:
        random_data.seek(0)
        data = random_data.read()
        checksum = hashlib.sha256(data).hexdigest()

        with NamedTemporaryFile() as encrypted_file:
            random_data.seek(0)
            private_key = crypt4gh.keys.get_private_key(
                filepath=config.data_dir / "key.sec", callback=lambda: None
            )
            pub_key = base64.b64decode("qx5g31H7rdsq7sgkew9ElkLIXvBje4RxDVcAHcJD8XY=")
            encryption_keys = [(0, private_key, pub_key)]
            crypt4gh.lib.encrypt(
                keys=encryption_keys, infile=random_data, outfile=encrypted_file
            )
            encrypted_file.seek(0)
            encrypted_data = encrypted_file.read()

            return data, encrypted_data, checksum
