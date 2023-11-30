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

"""Metadata related fixture"""

import base64
import os
import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings
from pytest import fixture

from fixtures.config import Config

BASE_DIR = Path(__file__).parent.parent
TMP_DIR = Path(tempfile.gettempdir())

KeyType = Literal["private", "public"]


def private_keyfile_content(raw_key: str) -> str:
    """Create content for unencrypted Crypt4GH private key file from raw encoded key."""
    magic_word = b"c4gh-v1"
    none = b"\x00\x04none"
    kdf = cipher = none
    comment = b""
    key = base64.b64decode(raw_key)
    key = len(key).to_bytes(2, "big") + key
    content_bytes = magic_word + kdf + cipher + key + comment
    content = base64.b64encode(content_bytes).decode("ascii")
    return content


def write_keyfile(path: Path, content: str, key_type: KeyType = "private"):
    if key_type == "private":
        content = private_keyfile_content(content)
    header = f"crypt4gh {key_type} key".upper()
    with open(path, "w", encoding="ascii") as file:
        file.write(f"-----BEGIN {header}-----\n")
        file.write(content)
        file.write(f"\n-----END {header}-----")


class ConnectorConfig(BaseSettings):
    """Config for metadata and related submissions"""

    work_dir: Path = TMP_DIR / "connector"
    user_public_key_path: Path = work_dir / "key.pub"
    user_private_key_path: Path = work_dir / "key.sec"
    download_dir: Path = work_dir / "download"


class ConnectorFixture:
    """GHGA Connector fixture"""

    config: ConnectorConfig

    def __init__(self, config: Config, connector_config: ConnectorConfig):
        self.config = connector_config
        wkvs_url = config.wkvs_url
        if wkvs_url:
            self.set_env("wkvs_api_url", wkvs_url)
        part_size = config.download_part_size
        if part_size:
            self.set_env("part_size", str(part_size))

    @staticmethod
    def set_env(key: str, value: str):
        os.environ[f"ghga_connector_{key}".upper()] = value

    def reset_work_dir(self):
        """Reset the working director for the GHGA connector."""
        work_dir = self.config.work_dir

        if os.path.exists(work_dir):
            shutil.rmtree(work_dir)

        work_dir.mkdir()
        self.config.download_dir.mkdir()

    def store_keys(self, public_key: str, private_key: str):
        """Store the given public and private keys in the working directory."""
        write_keyfile(self.config.user_public_key_path, public_key, "public")
        write_keyfile(self.config.user_private_key_path, private_key, "private")


@fixture(name="connector", scope="session")
def connector_fixture(config: Config) -> Generator[ConnectorFixture, None, None]:
    """Pytest fixture for tests using the GHGA Connector."""
    connector_config = ConnectorConfig()
    yield ConnectorFixture(config, connector_config)
