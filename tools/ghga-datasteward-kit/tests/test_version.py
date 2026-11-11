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

"""Tests the version the kit reports when run from a checkout."""

import pytest

from ghga_datasteward_kit import FALLBACK, __version__, checkout_version


@pytest.mark.parametrize(
    "described, expected",
    [
        ("ghga/15.3.1", "15.3.1"),
        ("ghga/15.3.1-rc.8", "15.3.1-rc.8"),
        ("ghga/15.3.1-dirty", "15.3.1+dirty"),
        ("ghga/15.3.1-rc.8-71-g44594f5", "15.3.1-rc.8+dev.71.44594f5"),
        ("ghga/15.3.1-rc.8-71-g44594f5c-dirty", "15.3.1-rc.8+dev.71.44594f5c.dirty"),
        ("v1.0.0", FALLBACK),
    ],
)
def test_checkout_version(described, expected):
    """`git describe` output maps to the format docs/releases.md defines."""
    assert checkout_version(described) == expected


def test_no_placeholder_reported():
    """Run from this checkout, the kit never reports the bare placeholder."""
    assert __version__ != "0.0.0"
