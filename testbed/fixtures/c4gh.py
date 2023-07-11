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

"""Fixture for testing functionality that needs Crypt4GH keys."""

from pathlib import Path
from typing import NamedTuple

from pytest import fixture

__all__ = ["c4gh_fixture", "C4GHKeyPair"]


KEY_FILE = Path(__file__).parent.parent / ".devcontainer/keys.env"


class C4GHKeyPair(NamedTuple):
    """A base64 encoded key pair as used in Crypt4GH."""

    private: str
    public: str


@fixture(name="c4gh")
def c4gh_fixture() -> C4GHKeyPair:
    """Fixture that provides a crypt4gh key pair."""
    with open(KEY_FILE, encoding="ascii") as key_file:
        public = private = None
        for line in key_file:
            if line.startswith("C4GH_PRIV="):
                private = line.split("=", 1)[1].rstrip()
            elif line.startswith("C4GH_PUB="):
                public = line.split("=", 1)[1].rstrip()
        if not public:
            raise ValueError("Missing public Crypt4GH key")
        if not private:
            raise ValueError("Missing private Crypt4GH key")
        return C4GHKeyPair(private, public)
