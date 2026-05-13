"""Tests for the public API.

Originally created on August 9, 2019 by Andrew Habib.
Contains changes by The GHGA Authors.
SPDX-License-Identifier: Apache-2.0
"""

import json

from jsonsubschema import (
    canonicalizeSchema,
    isEquivalent,
    isSubschema,
    joinSchemas,
    meetSchemas,
)
from jsonsubschema._canonicalization import simplify_schema_and_embed_checkers

s1 = {"type": "number"}
s2 = {"type": "integer"}

s_1 = '{"type": "number"}'
s_2 = '{"type": "integer"}'


def test_decoder_and_api():

    s1 = simplify_schema_and_embed_checkers(canonicalizeSchema(json.loads(s_1)))
    s2 = simplify_schema_and_embed_checkers(canonicalizeSchema(json.loads(s_2)))

    assert not s1.is_subtype(s2)

    assert s2.is_subtype(s1)

    assert s1.meet(s1) == s1

    assert s2.meet(s2) == s2

    assert s1.meet(s2) == s2.meet(s1)

    assert s1.join(s1) == joinSchemas(s1, s1)

    assert s2.join(s2) == joinSchemas(s2, s2)

    assert isEquivalent(s1.join(s2), s2.join(s1))

    assert (s1.meet(s2)).is_subtype(s2.meet(s1))

    assert (s2.meet(s1)).is_subtype(s1.meet(s2))

    assert (s1.join(s2)).is_subtype(s2.join(s1))

    assert (s2.join(s1)).is_subtype(s1.join(s2))


def test_api_is_subschema():

    assert not isSubschema(s1, s2)

    assert isSubschema(s2, s1)

    assert isSubschema(joinSchemas(s1, s2), joinSchemas(s2, s1))

    assert isSubschema(meetSchemas(s1, s2), meetSchemas(s2, s1))

    assert isSubschema(meetSchemas(s1, s2), joinSchemas(s2, s1))

    assert not isSubschema(joinSchemas(s1, s2), meetSchemas(s2, s1))


def test_api_meet():

    assert meetSchemas(s1, s2) == meetSchemas(s2, s1)

    assert meetSchemas(s1, s1) == s1

    assert meetSchemas(s2, s2) == s2


def test_api_join():

    assert isEquivalent(joinSchemas(s1, s2), joinSchemas(s2, s1))

    assert joinSchemas(s1, s1) == s1

    assert joinSchemas(s2, s2) == s2
