"""Tests for checker utility functions (top, bot, is_top, is_bot).

Originally created by Andrew Habib.
Contains changes by The GHGA Authors.
SPDX-License-Identifier: Apache-2.0
"""

from jsonsubschema._canonicalization import simplify_schema_and_embed_checkers
from jsonsubschema._checkers import JSONbot, JSONtop, is_bot, is_top

# Tests for is_top


def test_true_is_top() -> None:
    assert is_top(True)


def test_empty_object_is_top() -> None:
    assert is_top({})


def test_json_top_is_top() -> None:
    assert is_top(JSONtop())


def test_one_is_not_top() -> None:
    assert not is_top(1)


# Tests for is_bot


def test_false_is_bot() -> None:
    assert is_bot(False)


def test_not_empty_object_is_bot() -> None:
    assert is_bot({"not": {}})


def test_json_bot_is_bot() -> None:
    assert is_bot(JSONbot())


def test_uninhabited_schema_is_bot() -> None:
    uninhabited_schema = simplify_schema_and_embed_checkers(
        {"type": "integer", "minimum": 2, "maximum": 1}
    )
    assert is_bot(uninhabited_schema)


def test_zero_is_not_bot() -> None:
    assert not is_bot(0)
