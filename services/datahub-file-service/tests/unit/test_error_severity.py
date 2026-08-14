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

"""Tests for picking the error to surface when concurrent parts or files fail.

Parts run inside nested TaskGroups, so failures can arrive wrapped several layers deep
and severity has to survive that nesting.
"""

import asyncio

import pytest

from dhfs.core.interrogator import (
    InterrogatorPort,
    _collapsing_error_groups,
    _flatten_exception_group,
    _most_significant_error,
)

CRITICAL = InterrogatorPort.CriticalError("critical")
CONCLUSIVE = InterrogatorPort.DecryptionError()
INCONCLUSIVE = InterrogatorPort.InconclusiveError("inconclusive")


def test_flatten_nested_groups():
    """Leaves are collected from arbitrarily deep ExceptionGroups."""
    group = ExceptionGroup(
        "outer",
        [
            ExceptionGroup("inner", [INCONCLUSIVE, CRITICAL]),
            ExceptionGroup("also inner", [ExceptionGroup("deep", [CONCLUSIVE])]),
        ],
    )
    assert _flatten_exception_group(group) == [INCONCLUSIVE, CRITICAL, CONCLUSIVE]


@pytest.mark.parametrize(
    "errors, expected",
    [
        ([INCONCLUSIVE, CRITICAL], CRITICAL),
        ([INCONCLUSIVE, CONCLUSIVE], CONCLUSIVE),
        ([CONCLUSIVE, CRITICAL], CRITICAL),
        ([INCONCLUSIVE, CONCLUSIVE, CRITICAL], CRITICAL),
        ([INCONCLUSIVE], INCONCLUSIVE),
    ],
    ids=[
        "critical beats inconclusive",
        "conclusive beats inconclusive",
        "critical beats conclusive",
        "critical beats both",
        "lone inconclusive survives",
    ],
)
def test_severity_wins_regardless_of_position(errors, expected):
    """The most severe error is surfaced no matter what order the parts failed in."""
    for ordering in (errors, list(reversed(errors))):
        group = ExceptionGroup("parts failed", ordering)
        assert _most_significant_error(group) is expected


def test_severity_survives_the_nested_part_group():
    """A CriticalError still wins when it is raised a level deeper than its rival.

    This is the shape the overlapped verify/upload pair produces: the per-part group
    is nested inside the per-file group.
    """
    group = ExceptionGroup(
        "file",
        [
            INCONCLUSIVE,
            ExceptionGroup("part", [CRITICAL]),
        ],
    )
    assert _most_significant_error(group) is CRITICAL


def test_collapsing_surfaces_the_most_significant_error():
    """The happy path: an ordinary ExceptionGroup collapses to its worst member."""
    with pytest.raises(InterrogatorPort.CriticalError) as exc_info:
        with _collapsing_error_groups():
            raise ExceptionGroup("parts failed", [INCONCLUSIVE, CRITICAL])

    assert exc_info.value is CRITICAL


def test_cancellation_is_not_downgraded_to_a_retry():
    """A cancelled batch must not be reported as a file that merely needs retrying.

    `CancelledError` is a BaseException, so a TaskGroup carrying one raises a
    `BaseExceptionGroup` rather than an `ExceptionGroup`. Catching the broader type
    would let the concurrent InconclusiveError outrank the cancellation and turn a
    shutdown into an endless retry.
    """
    with pytest.raises(BaseExceptionGroup) as exc_info:
        with _collapsing_error_groups():
            raise BaseExceptionGroup(
                "batch cancelled", [INCONCLUSIVE, asyncio.CancelledError()]
            )

    # The group passed straight through instead of collapsing to INCONCLUSIVE
    assert not isinstance(exc_info.value, InterrogatorPort.InconclusiveError)
    assert len(exc_info.value.exceptions) == 2


@pytest.mark.parametrize(
    "base_error", [asyncio.CancelledError(), KeyboardInterrupt(), SystemExit()]
)
def test_base_exceptions_propagate_untouched(base_error):
    """Nothing that stops the process may be swallowed by the severity ranking."""
    with pytest.raises(BaseExceptionGroup):
        with _collapsing_error_groups():
            raise BaseExceptionGroup("stopping", [base_error])
