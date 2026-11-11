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

"""Test schemapack without its optional `schema-comparison` extra."""

import importlib
import sys

import pytest

from arcticfreeze import FrozenDict


@pytest.fixture
def without_jsonsubschema(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make jsonsubschema unimportable and forget the imported schemapack modules."""
    for name in list(sys.modules):
        if name == "schemapack" or name.startswith("schemapack."):
            monkeypatch.delitem(sys.modules, name)
    # A None entry makes `import jsonsubschema` raise ImportError.
    monkeypatch.setitem(sys.modules, "jsonsubschema", None)


@pytest.mark.usefixtures("without_jsonsubschema")
def test_import_without_jsonsubschema():
    """Test that schemapack and its CLI import without ghga-jsonsubschema."""
    schemapack = importlib.import_module("schemapack")
    main = importlib.import_module("schemapack.__main__")

    assert callable(schemapack.load_and_validate)
    assert callable(main.cli)


@pytest.mark.usefixtures("without_jsonsubschema")
def test_comparison_without_jsonsubschema():
    """Test that a semantic comparison names the missing extra."""
    compare = importlib.import_module("schemapack._internals.compare")
    schema = FrozenDict({"type": "object"})

    with pytest.raises(ImportError, match=r"schemapack\[schema-comparison\]"):
        compare.compare_content_semantically(schema, schema)
