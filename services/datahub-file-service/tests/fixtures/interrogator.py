# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Helpers for building an Interrogator in isolation from its collaborators."""

from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import MagicMock

from dhfs.core.interrogator import Interrogator
from tests.fixtures.config import get_config
from tests.fixtures.utils import DHFS_CRYPT4GH_PRIVATE_KEY_PATH


@contextmanager
def make_interrogator(**config_overrides) -> Iterator[Interrogator]:
    """An Interrogator with mocked-out collaborators, closed again on exit.

    Only the interrogator's own logic is exercised - the Central API and S3 clients
    are mocks. Closing matters because every instance owns a crypto thread pool.
    """
    config = get_config(
        data_hub_crypt4gh_private_key_path=DHFS_CRYPT4GH_PRIVATE_KEY_PATH,
        **config_overrides,
    )
    interrogator = Interrogator(
        config=config, central_client=MagicMock(), s3_client=MagicMock()
    )
    try:
        yield interrogator
    finally:
        interrogator.close()
