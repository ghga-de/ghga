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

"""Functionality for file downloading"""

from pathlib import Path

import crypt4gh
import crypt4gh.keys
import crypt4gh.lib
from ghga_connector.cli import download

from src.config import Config


def download_file(output_dir: Path, config: Config):
    """Download a file"""
    download(
        output_dir=output_dir,
        submitter_private_key_path=config.data_dir / "key.sec",
        submitter_pubkey_path=config.data_dir / "key.pub",
    )


def decrypt_file(input_location: Path, output_location: Path, config: Config):
    """Decrypt file"""
    private_key = crypt4gh.keys.get_private_key(
        filepath=config.data_dir / "key.sec", callback=lambda: None
    )
    decryption_keys = [(0, private_key, None)]

    with input_location.open("rb") as encrypted:
        with output_location.open("wb") as decrypted:
            crypt4gh.lib.decrypt(
                keys=decryption_keys, infile=encrypted, outfile=decrypted
            )
