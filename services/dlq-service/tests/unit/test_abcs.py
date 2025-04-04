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
"""Development-centered tests to keep ABC classes and their implementations in sync"""

import inspect

import pytest

from dlqs.adapters.outbound.dao import Aggregator
from dlqs.core.dlq_manager import DLQManager
from dlqs.ports.inbound.dlq_manager import DLQManagerPort
from dlqs.ports.outbound.dao import AggregatorPort


@pytest.mark.parametrize(
    "abc_class, imp_class, methods",
    [
        (
            DLQManagerPort,
            DLQManager,
            ["store_event", "preview_events", "process_event", "discard_event"],
        ),
        (
            AggregatorPort,
            Aggregator,
            ["aggregate"],
        ),
    ],
)
def test_dlq_manager_sigs(abc_class: type, imp_class: type, methods: list[str]):
    """Test that abstract/concrete doc strings and signatures are matching"""
    for method in methods:
        abc_method = getattr(abc_class, method)
        imp_method = getattr(imp_class, method)
        assert imp_method.__doc__ == abc_method.__doc__, f"{method} doc string mismatch"
        assert inspect.signature(imp_method) == inspect.signature(abc_method), (
            f"{method} function signature mismatch"
        )
