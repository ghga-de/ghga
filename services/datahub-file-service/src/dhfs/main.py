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

from dhfs import __version__
from dhfs.config import Config
from dhfs.core.interrogator import InterrogatorPort
from dhfs.core.verifier import run_dhfs_verification
from dhfs.inject import prepare_interrogation_bucket_cleaner, prepare_interrogator
from hexkit.log import configure_logging
from hexkit.utils import now_utc_ms_prec

log = logging.getLogger(__name__)


def _configure_logging(config: Config):
    """Silence log messages from libraries and set up structured logging.

    Loggers defined in `config.library_logger_names` will be set to
    `config.library_log_level`. If the general `config.log_level` is higher, then that
    takes precedence. This provides granular control over DHFS's logging output.
    """
    configure_logging(config=config)
    for logger in config.library_logger_names:
        logging.getLogger(logger).setLevel(config.library_log_level)


async def run_interrogator(forever: bool = True):
    """Run the file interrogation and re-encryption process."""
    config = Config()
    _configure_logging(config=config)
    log.info("DHFS version %s starting.", __version__)
    async with prepare_interrogator(config=config) as interrogator:
        if forever:
            while True:
                try:
                    start = now_utc_ms_prec()
                    await interrogator.interrogate_new_files()
                except InterrogatorPort.CriticalError as err:
                    log.critical(
                        "DHFS cannot continue processing until the following error is resolved: %s",
                        err,
                    )
                    return
                except Exception as err:
                    log.error(
                        "An unhandled exception caused the current batch of file"
                        + " processing to fail. If this keeps occurring, try running"
                        + " with log_level set to DEBUG for more information.",
                        extra={"exc": err},
                    )

                stop = now_utc_ms_prec()
                # .seconds would drop whole days and the sub-second remainder
                elapsed = (stop - start).total_seconds()
                if elapsed < config.min_run_interval_seconds:
                    sleep_duration = config.min_run_interval_seconds - elapsed
                    log.info(
                        "Waiting %.1f seconds before beginning the next round of file"
                        + " processing because the minimum run interval is set to"
                        + " %i seconds.",
                        sleep_duration,
                        config.min_run_interval_seconds,
                    )
                    await sleep(sleep_duration)
        else:
            await interrogator.interrogate_new_files()


async def perform_cleanup():
    """Run the S3 'interrogation' bucket cleanup routine."""
    config = Config()
    _configure_logging(config=config)
    log.info("Cleanup routine starting. Current DHFS version is %s.", __version__)
    async with prepare_interrogation_bucket_cleaner(config=config) as cleaner:
        await cleaner.scan_and_clean()


async def verify(*, file_size: int = 125 * 1024**2):
    """Run the re-encryption process on a dummy file to verify that DHFS works with the
    current S3 backend.
    """
    config = Config()
    _configure_logging(config=config)
    log.info(
        "Starting DHFS test run against real S3 backend. Current DHFS version is %s.",
        __version__,
    )
    start = now_utc_ms_prec()
    await run_dhfs_verification(config=config, file_size=file_size)
    stop = now_utc_ms_prec()
    duration_sec = (stop - start).total_seconds()
    log.info(
        "S3 verification process took %.1f seconds, including cleanup.", duration_sec
    )
