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

"""Retry helper for DAO updates that can lose a race condition."""

from asyncio import sleep
from collections.abc import AsyncIterator, Callable
from logging import Logger
from random import uniform
from types import TracebackType

from hexkit.protocols.dao import PreconditionFailedError

__all__ = ["RaceConditionAttempt", "race_condition_retries"]


class RaceConditionAttempt:
    """A single try yielded by `race_condition_retries`.

    Used as a context manager: suppresses a `PreconditionFailedError` raised in its block,
    keeps it in `error`, and records whether the block was entered and whether it
    finished without one.
    """

    def __init__(self) -> None:
        self.entered = False
        self.succeeded = False
        self.error: PreconditionFailedError | None = None

    def __enter__(self) -> None:
        """Start the attempt."""
        self.entered = True

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        """Record the outcome and suppress a `PreconditionFailedError`."""
        if exc_type is None:
            self.succeeded = True
            return False
        if isinstance(exc_value, PreconditionFailedError):
            self.error = exc_value
            return True
        return False


async def race_condition_retries(  # noqa: PLR0913
    *,
    description: str,
    error_on_failure: Callable[[], BaseException],
    logger: Logger | None = None,
    max_tries: int = 3,
    interval: float = 0.5,
    jitter: float = 0.3,
) -> AsyncIterator[RaceConditionAttempt]:
    """Yield attempts for an action that can lose a race condition.

    Wrap the action in `with attempt:` for each yielded attempt. Retries it up to
    `max_tries` times, waiting `interval` seconds (plus jitter) after each
    `PreconditionFailedError`. That error means the `precondition` of a DAO update no
    longer matched because another write came first. A `return` inside the block
    ends the retries.

    ```python
    async for attempt in race_condition_retries(
        description=f"add pages to book {book_id}",
        error_on_failure=lambda: BookUpdateError(book_id),
    ):
        with attempt:  # <-- must use `with attempt:`
            book = await book_dao.get_by_id(book_id)
            extended = book.model_copy(update={"pages": book.pages + 16})
            await book_dao.update(extended, precondition={"pages": book.pages})
    ```

    Leaving the loop early, by `return`, `break` or an exception, leaves the generator
    suspended until asyncio finalizes it. For deterministic cleanup, wrap it in
    `contextlib.aclosing`:

    ```python
    async with aclosing(race_condition_retries(...)) as attempts:
        async for attempt in attempts:
            with attempt:
                ...
    ```

    Args:
        description:
            What the action does, phrased to follow "to", e.g.
            "add pages to book <book_id>". Used in log messages.
        error_on_failure:
            Builds the error to raise once all tries have failed. Called at most once,
            after the last try.
        logger:
            Logs a debug message for each conflict and an error once all tries have
            failed. Nothing is logged if omitted.
        max_tries: How many times to try the action. Values below 1 count as 1.
        interval: Seconds to wait between tries. Negative values count as 0.
        jitter:
            Upper bound, in seconds, of a random delay added to each wait, so callers
            that conflicted don't retry at the same moment. Negative values count as 0.

    Raises:
    - The error built by `error_on_failure` if the action still raises
      `PreconditionFailedError` on the last try. It is chained from that last
      `PreconditionFailedError`.
    - `RuntimeError` if a yielded attempt was not used as `with attempt:`.
    """
    description = description.strip(" .")
    tries = max(1, max_tries)
    last_error: PreconditionFailedError | None = None
    for attempt_number in range(1, tries + 1):
        attempt = RaceConditionAttempt()
        yield attempt
        if not attempt.entered:
            raise RuntimeError(
                "Each attempt yielded by race_condition_retries must be used as"
                " `with attempt:`."
            )
        if attempt.succeeded:
            return
        last_error = attempt.error
        if logger:
            logger.debug("Detected race condition while trying to %s.", description)
        if attempt_number < tries:
            await sleep(max(0, interval) + uniform(0, max(jitter, 0)))  # noqa: S311

    if logger:
        logger.error(
            "Failed %s times to %s due to persistent race conditions.",
            tries,
            description,
        )
    raise error_on_failure() from last_error
