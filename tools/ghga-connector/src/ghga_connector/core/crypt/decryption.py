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
"""This module contains Crypt4GH based decryption functionality"""

from pathlib import Path

import crypt4gh.keys
import crypt4gh.lib

from .abstract_bases import Decryptor


class Crypt4GHDecryptor(Decryptor):
    """Convenience class to deal with Crypt4GH decryption"""

    def __init__(self, decryption_key_path: Path):
        self._decryption_key = crypt4gh.keys.get_private_key(
            decryption_key_path, callback=None
        )

    def decrypt_file(self, *, input_path: Path, output_path: Path):
        """Decrypt provided file using Crypt4GH lib"""
        keys = [(0, self._decryption_key, None)]
        with input_path.open("rb") as infile, output_path.open("wb") as outfile:
            crypt4gh.lib.decrypt(keys=keys, infile=infile, outfile=outfile)
