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
"""Service configuration and execution"""

import logging
from asyncio import sleep

from hexkit.log import configure_logging
from hexkit.utils import now_utc_ms_prec

from dhfs import __version__
from dhfs.config import Config
from dhfs.inject import prepare_interrogation_bucket_cleaner, prepare_interrogator

log = logging.getLogger(__name__)


async def run_interrogator(forever: bool = True):
    """Run the file interrogation and re-encryption process."""
    config = Config()  # type: ignore
    configure_logging(config=config)
    log.info("DHFS version %s starting.", __version__)
    async with prepare_interrogator(config=config) as interrogator:
        if forever:
            while True:
                try:
                    start = now_utc_ms_prec()
                    await interrogator.interrogate_new_files()
                except Exception:
                    log.warning(
                        "An unhandled exception occurred (see logs for more details)."
                        + " Beginning fresh interrogation loop.",
                        exc_info=True,
                    )
                finally:
                    stop = now_utc_ms_prec()
                    if (
                        timediff := (stop - start).seconds
                    ) < config.min_run_interval_seconds:
                        sleep_duration = config.min_run_interval_seconds - timediff
                        log.info(
                            "Waiting %i seconds because minimum run interval is set to %i.",
                            sleep_duration,
                            config.min_run_interval_seconds,
                        )
                        await sleep(sleep_duration)
        else:
            await interrogator.interrogate_new_files()


async def perform_cleanup():
    """Run the S3 'interrogation' bucket cleanup routine."""
    config = Config()  # type: ignore
    configure_logging(config=config)
    log.info("Cleanup routine starting. Current DHFS version is %s.", __version__)
    async with prepare_interrogation_bucket_cleaner(config=config) as cleaner:
        await cleaner.scan_and_clean()
