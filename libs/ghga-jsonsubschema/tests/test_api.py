"""Tests for the public API.

Originally created on August 9, 2019 by Andrew Habib.
Contains changes by The GHGA Authors.
SPDX-License-Identifier: Apache-2.0
"""

import json

from jsonsubschema import (
    canonicalize_schema,
    is_equivalent,
    is_subschema,
    join_schemas,
    meet_schemas,
)
from jsonsubschema._canonicalization import simplify_schema_and_embed_checkers

s1 = {"type": "number"}
s2 = {"type": "integer"}

s_1 = '{"type": "number"}'
s_2 = '{"type": "integer"}'


def test_decoder_and_api():

    s1 = simplify_schema_and_embed_checkers(canonicalize_schema(json.loads(s_1)))
    s2 = simplify_schema_and_embed_checkers(canonicalize_schema(json.loads(s_2)))

    assert not s1.is_subtype(s2)

    assert s2.is_subtype(s1)

    assert s1.meet(s1) == s1

    assert s2.meet(s2) == s2

    assert s1.meet(s2) == s2.meet(s1)

    assert s1.join(s1) == join_schemas(s1, s1)

    assert s2.join(s2) == join_schemas(s2, s2)

    assert is_equivalent(s1.join(s2), s2.join(s1))

    assert (s1.meet(s2)).is_subtype(s2.meet(s1))

    assert (s2.meet(s1)).is_subtype(s1.meet(s2))

    assert (s1.join(s2)).is_subtype(s2.join(s1))

    assert (s2.join(s1)).is_subtype(s1.join(s2))


def test_api_is_subschema():

    assert not is_subschema(s1, s2)

    assert is_subschema(s2, s1)

    assert is_subschema(join_schemas(s1, s2), join_schemas(s2, s1))

    assert is_subschema(meet_schemas(s1, s2), meet_schemas(s2, s1))

    assert is_subschema(meet_schemas(s1, s2), join_schemas(s2, s1))

    assert not is_subschema(join_schemas(s1, s2), meet_schemas(s2, s1))


def test_api_meet():

    assert meet_schemas(s1, s2) == meet_schemas(s2, s1)

    assert meet_schemas(s1, s1) == s1

    assert meet_schemas(s2, s2) == s2


def test_api_join():

    assert is_equivalent(join_schemas(s1, s2), join_schemas(s2, s1))

    assert join_schemas(s1, s1) == s1

    assert join_schemas(s2, s2) == s2
