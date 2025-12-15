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
"""Service configuration and execution"""

from hexkit.log import configure_logging

from dhfs.config import Config


async def run_interrogator():
    """Run the file interrogation and re-encryption process."""
    config = Config()  # type: ignore
    configure_logging(config=config)

    raise NotImplementedError()


async def perform_cleanup():
    """Run the S3 'interrogation' bucket cleanup routine."""
    config = Config()  # type: ignore
    configure_logging(config=config)

    raise NotImplementedError()
