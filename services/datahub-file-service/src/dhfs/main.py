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

from asyncio import sleep

from hexkit.log import configure_logging
from hexkit.utils import now_utc_ms_prec

from dhfs.config import Config
from dhfs.inject import prepare_interrogation_bucket_cleaner, prepare_interrogator


async def run_interrogator(forever: bool = True):
    """Run the file interrogation and re-encryption process."""
    config = Config()  # type: ignore
    configure_logging(config=config)
    async with prepare_interrogator(config=config) as interrogator:
        if forever:
            while True:
                start = now_utc_ms_prec()
                await interrogator.interrogate_new_files()
                stop = now_utc_ms_prec()
                if (
                    timediff := (stop - start).seconds
                ) < config.min_run_interval_seconds:
                    await sleep(config.min_run_interval_seconds - timediff)
        else:
            await interrogator.interrogate_new_files()


async def perform_cleanup():
    """Run the S3 'interrogation' bucket cleanup routine."""
    config = Config()  # type: ignore
    configure_logging(config=config)

    async with prepare_interrogation_bucket_cleaner(config=config) as cleaner:
        await cleaner.scan_and_clean()
