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
#

"""Util functions for accession registry"""

import secrets
from collections.abc import Callable


def generate_random_block(alphabet: str, random_block_length: int) -> str:
    """Return a random block of a certain length from an alphabet, e.g., base 32"""
    return "".join(secrets.choice(alphabet) for _ in range(random_block_length))


def random_block_at(alphabet: str, random_block_length: int, index: int) -> str:
    """Return the random block at the given index of the space of all random
    blocks, reading the index as a number in an alphabet, e.g., base 32.
    """
    characters = []
    for _ in range(random_block_length):
        index, remainder = divmod(index, len(alphabet))
        characters.append(alphabet[remainder])

    return "".join(reversed(characters))


def split_study_pid(study_pid: str) -> tuple[str, str] | None:
    """Return the year and the random block of the study PID 'PREFIX.YY.XXX.V', or
    None for a flat accession from before study PIDs.
    """
    # split from the right, so that the prefix does not matter
    parts = study_pid.rsplit(".", 3)
    if len(parts) != 4:
        return None

    _, year, random_block, _ = parts
    return year, random_block


def find_unused_pid(
    alphabet: str,
    random_block_length: int,
    compose: Callable[[str], str],
    used_pids: set[str],
) -> str | None:
    """Find a PID not in `used_pids`, composing candidates from random blocks.

    Starts at a random index of the space of all random blocks and walks it, wrapping
    around, holding one candidate at a time. Returns None if every PID is used.
    """
    space_size = len(alphabet) ** random_block_length
    start = secrets.randbelow(space_size)

    for step in range(space_size):
        random_block = random_block_at(
            alphabet, random_block_length, (start + step) % space_size
        )
        pid = compose(random_block)
        if pid not in used_pids:
            return pid

    return None
