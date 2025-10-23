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

"""Task management that supplies TaskGroup-esque functionality for python <3.10"""

import asyncio
import logging
from asyncio import Task, create_task
from collections.abc import Coroutine
from typing import Any

log = logging.getLogger(__name__)


class TaskHandler:
    """Wraps task scheduling details."""

    def __init__(self):
        self._tasks: set[Task] = set()

    def schedule(self, fn: Coroutine[Any, Any, None]):
        """Create a task and register its callback."""
        task = create_task(fn)
        self._tasks.add(task)
        task.add_done_callback(self.finalize)

    def cancel_tasks(self):
        """Cancel all running tasks."""
        for task in self._tasks:
            if not task.done():
                task.cancel()

    def finalize(self, task: Task):
        """Deal with potential errors when a task is done.

        This is called as done callback, so there are three possibilities here:
        1. A task encountered an exception: Cancel all remaining tasks and reraise
        2. A task was cancelled: There's nothing to do, we are already propagating
           the exception causing the cancellation
        3. A task finished normally: Remove its handle
        """
        if not task.cancelled():
            exception = task.exception()
            if exception:
                self.cancel_tasks()
                raise exception
        self._tasks.discard(task)
        log.debug(
            "Finished task. Remaining: %i",
            len([task for task in asyncio.all_tasks() if not task.done()]),
        )

    async def gather(self):
        """Await all remaining tasks."""
        await asyncio.gather(*self._tasks)
