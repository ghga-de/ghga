"""Additional tests for subschema checking edge cases.

Originally created on July 11, 2019 by Andrew Habib.
Contains changes by The GHGA Authors.
SPDX-License-Identifier: Apache-2.0
"""

import pytest

from jsonsubschema import is_equivalent, is_subschema

# Tests with paper examples


def test_obj():
    s1 = {
        "anyOf": [
            {"type": "array"},
            {"type": "boolean"},
            {"type": "integer"},
            {"type": "null"},
            {"type": "number"},
            {
                "additionalProperties": False,
                "properties": {
                    "type": {
                        "type": "string",
                        "pattern": "^reference$",
                        "enum": ["reference"],
                    },
                    "additional_properties": {
                        "type": "object",
                        "additionalProperties": True,
                    },
                    "referent": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "type": {"type": "string"},
                            "service": {"type": "string"},
                            "id": {"type": "string"},
                            "provider": {"type": "string"},
                        },
                        "required": ["id", "provider"],
                    },
                },
                "required": ["referent", "type"],
                "type": "object",
            },
            {"type": "string"},
        ]
    }

    s2 = {
        "anyOf": [
            {"type": "array"},
            {"type": "boolean"},
            {"type": "integer"},
            {"type": "null"},
            {"type": "number"},
            {
                "additionalProperties": False,
                "properties": {
                    "type": {
                        "type": "string",
                        "pattern": "^reference$",
                        "enum": ["reference"],
                    },
                    "additional_properties": {
                        "type": "object",
                        "additionalProperties": True,
                    },
                    "_id": {"type": "string"},
                    "subtype": {"type": "string"},
                    "channels": {"type": "array", "items": {"type": "string"}},
                    "referent": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "type": {"type": "string"},
                            "service": {"type": "string"},
                            "id": {"type": "string"},
                            "provider": {"type": "string"},
                            "referent_properties": {
                                "additionalProperties": True,
                                "type": "object",
                            },
                        },
                        "required": ["id", "provider"],
                    },
                },
                "required": ["referent", "type"],
                "type": "object",
            },
            {"type": "string"},
        ]
    }

    assert is_subschema(s1, s2)


def test_simple_list_of_type():
    s1 = {"type": ["array", "object"]}
    s2 = {"type": ["object", "array"]}

    assert is_equivalent(s1, s2)


def test_equiv_multiple_case():
    s1 = {"type": ["string", "null"], "minLength": 1}
    s2 = {"type": ["null", "string"], "pattern": ".+"}
    s3 = {"anyOf": [{"type": "string", "pattern": ".{1,}"}, {"enum": [None]}]}
    s4 = {"anyOf": [{"type": "string"}, {"type": "null"}], "not": {"enum": [""]}}

    assert is_equivalent(s1, s2)
    assert is_equivalent(s1, s3)
    assert is_equivalent(s1, s4)
    assert is_equivalent(s2, s3)
    assert is_equivalent(s2, s4)
    assert is_equivalent(s3, s4)


def test_bool_enum():
    s1 = {"type": "boolean", "enum": [True], "not": {"enum": [True]}}
    s2: dict = {"allOf": [{}, {"not": {}}]}
    assert is_subschema(s1, s2)
    assert is_equivalent(s1, s2)


def test_bool_enum2():
    s1 = {"enum": [True, False]}
    s2 = {"enum": [True]}
    assert is_subschema(s2, s1)
    assert not is_subschema(s1, s2)
    assert not is_equivalent(s1, s2)

    s3 = {"allOf": [s1, s2]}
    assert is_subschema(s3, s1)
    assert is_subschema(s3, s2)
    assert not is_subschema(s1, s3)
    assert is_equivalent(s2, s3)

    s4 = {"anyOf": [s1, s2]}
    assert is_subschema(s1, s4)
    assert is_subschema(s2, s4)
    assert not is_subschema(s4, s2)
    assert is_equivalent(s1, s4)


@pytest.mark.skip(reason="Unsupported array join")
def test_union_of_tuples():
    t1 = {"type": "string", "maxLength": 1}
    t2 = {"type": "integer"}
    t = {"type": "array"}

    s1 = {
        "type": "array",
        "items": [{"anyOf": [t1, t2]}, t],
        "additionalItems": False,
        "minItems": 2,
    }
    s2 = {
        "anyOf": [
            {
                "type": "array",
                "items": [t1, t],
                "additionalItems": False,
                "minItems": 2,
            },
            {
                "type": "array",
                "items": [t2, t],
                "additionalItems": False,
                "minItems": 2,
            },
        ]
    }
    assert is_subschema(s2, s1)
    assert is_equivalent(s1, s2)


# Tests with BigchainDB examples


def test_transaction_create():
    v1 = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "title": "Transaction Schema - CREATE/GENESIS specific constraints",
        "required": ["asset", "inputs"],
        "properties": {
            "asset": {
                "additionalProperties": False,
                "properties": {
                    "data": {
                        "anyOf": [
                            {"type": "object", "additionalProperties": True},
                            {"type": "null"},
                        ]
                    }
                },
                "required": ["data"],
            },
            "inputs": {
                "type": "array",
                "title": "Transaction inputs",
                "maxItems": 1,
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["fulfills"],
                    "properties": {"fulfills": {"type": "null"}},
                },
            },
        },
    }

    v2 = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "title": "Transaction Schema - CREATE specific constraints",
        "required": ["asset", "inputs"],
        "properties": {
            "asset": {
                "additionalProperties": False,
                "properties": {
                    "data": {
                        "anyOf": [
                            {"type": "object", "additionalProperties": True},
                            {"type": "null"},
                        ]
                    }
                },
                "required": ["data"],
            },
            "inputs": {
                "type": "array",
                "title": "Transaction inputs",
                "maxItems": 1,
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["fulfills"],
                    "properties": {"fulfills": {"type": "null"}},
                },
            },
        },
    }

    assert is_equivalent(v1, v2)


def test_transaction_transfer():
    v1 = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "title": "Transaction Schema - TRANSFER specific properties",
        "required": ["asset"],
        "properties": {
            "asset": {
                "additionalProperties": False,
                "properties": {"id": {"$ref": "#/definitions/sha3_hexdigest"}},
                "required": ["id"],
            },
            "inputs": {
                "type": "array",
                "title": "Transaction inputs",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["fulfills"],
                    "properties": {"fulfills": {"type": "object"}},
                },
            },
        },
        "definitions": {
            "sha3_hexdigest": {"pattern": "[0-9a-f]{64}", "type": "string"}
        },
    }

    v2 = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "title": "Transaction Schema - TRANSFER specific properties",
        "required": ["asset"],
        "properties": {
            "asset": {
                "additionalProperties": False,
                "properties": {"id": {"$ref": "#/definitions/sha3_hexdigest"}},
                "required": ["id"],
            },
            "inputs": {
                "type": "array",
                "title": "Transaction inputs",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["fulfills"],
                    "properties": {"fulfills": {"type": "object"}},
                },
            },
        },
        "definitions": {
            "sha3_hexdigest": {"pattern": "[0-9a-f]{64}", "type": "string"}
        },
    }

    assert is_equivalent(v1, v2)


def test_transaction_create_transfer():
    create_v1 = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "title": "Transaction Schema - CREATE/GENESIS specific constraints",
        "required": ["asset", "inputs"],
        "properties": {
            "asset": {
                "additionalProperties": False,
                "properties": {
                    "data": {
                        "anyOf": [
                            {"type": "object", "additionalProperties": True},
                            {"type": "null"},
                        ]
                    }
                },
                "required": ["data"],
            },
            "inputs": {
                "type": "array",
                "title": "Transaction inputs",
                "maxItems": 1,
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["fulfills"],
                    "properties": {"fulfills": {"type": "null"}},
                },
            },
        },
    }

    create_v2 = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "title": "Transaction Schema - CREATE specific constraints",
        "required": ["asset", "inputs"],
        "properties": {
            "asset": {
                "additionalProperties": False,
                "properties": {
                    "data": {
                        "anyOf": [
                            {"type": "object", "additionalProperties": True},
                            {"type": "null"},
                        ]
                    }
                },
                "required": ["data"],
            },
            "inputs": {
                "type": "array",
                "title": "Transaction inputs",
                "maxItems": 1,
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["fulfills"],
                    "properties": {"fulfills": {"type": "null"}},
                },
            },
        },
    }

    transfer_v1 = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "title": "Transaction Schema - TRANSFER specific properties",
        "required": ["asset"],
        "properties": {
            "asset": {
                "additionalProperties": False,
                "properties": {"id": {"$ref": "#/definitions/sha3_hexdigest"}},
                "required": ["id"],
            },
            "inputs": {
                "type": "array",
                "title": "Transaction inputs",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["fulfills"],
                    "properties": {"fulfills": {"type": "object"}},
                },
            },
        },
        "definitions": {
            "sha3_hexdigest": {"pattern": "[0-9a-f]{64}", "type": "string"}
        },
    }

    transfer_v2 = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "title": "Transaction Schema - TRANSFER specific properties",
        "required": ["asset"],
        "properties": {
            "asset": {
                "additionalProperties": False,
                "properties": {"id": {"$ref": "#/definitions/sha3_hexdigest"}},
                "required": ["id"],
            },
            "inputs": {
                "type": "array",
                "title": "Transaction inputs",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["fulfills"],
                    "properties": {"fulfills": {"type": "object"}},
                },
            },
        },
        "definitions": {
            "sha3_hexdigest": {"pattern": "[0-9a-f]{64}", "type": "string"}
        },
    }

    assert not is_subschema(transfer_v1, create_v1)
    assert not is_subschema(transfer_v2, create_v2)

    assert not is_subschema(create_v1, transfer_v1)
    assert not is_subschema(create_v2, transfer_v2)


def test_transaction():
    """
    Origial schemas were recursive on condition_details in
    '#/definitions/condition_details'.
    To test them, I unrolled couple of recursion levels by
    manually  nesting the schema, then eventually I broke recursion
    by suplying a non-recursive schema in the inner most level of
    "subconditions': {'type': 'array', 'items': { ..."
    """
    v1 = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "additionalProperties": False,
        "title": "Transaction Schema",
        "required": [
            "id",
            "inputs",
            "outputs",
            "operation",
            "metadata",
            "asset",
            "version",
        ],
        "properties": {
            "id": {
                "anyOf": [
                    {"$ref": "#/definitions/sha3_hexdigest"},
                    {"type": "null"},
                ]
            },
            "operation": {"$ref": "#/definitions/operation"},
            "asset": {"$ref": "#/definitions/asset"},
            "inputs": {
                "type": "array",
                "title": "Transaction inputs",
                "items": {"$ref": "#/definitions/input"},
            },
            "outputs": {"type": "array", "items": {"$ref": "#/definitions/output"}},
            "metadata": {"$ref": "#/definitions/metadata"},
            "version": {"type": "string", "pattern": "^1\\.0$"},
        },
        "definitions": {
            "offset": {"type": "integer", "minimum": 0},
            "base58": {"pattern": "[1-9a-zA-Z^OIl]{43,44}", "type": "string"},
            "public_keys": {
                "anyOf": [
                    {"type": "array", "items": {"$ref": "#/definitions/base58"}},
                    {"type": "null"},
                ]
            },
            "sha3_hexdigest": {"pattern": "[0-9a-f]{64}", "type": "string"},
            "uuid4": {
                "pattern": "[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}",  # noqa: E501
                "type": "string",
            },
            "operation": {
                "type": "string",
                "enum": ["CREATE", "TRANSFER", "GENESIS"],
            },
            "asset": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "id": {"$ref": "#/definitions/sha3_hexdigest"},
                    "data": {
                        "anyOf": [
                            {"type": "object", "additionalProperties": True},
                            {"type": "null"},
                        ]
                    },
                },
            },
            "output": {
                "type": "object",
                "additionalProperties": False,
                "required": ["amount", "condition", "public_keys"],
                "properties": {
                    "amount": {"type": "string", "pattern": "^[0-9]{1,20}$"},
                    "condition": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["details", "uri"],
                        "properties": {
                            "details": {"$ref": "#/definitions/condition_details"},
                            "uri": {
                                "type": "string",
                                "pattern": "^ni:///sha-256;([a-zA-Z0-9_-]{0,86})[?](fpt=(ed25519|threshold)-sha-256(&)?|cost=[0-9]+(&)?|subtypes=ed25519-sha-256(&)?){2,3}$",
                            },
                        },
                    },
                    "public_keys": {"$ref": "#/definitions/public_keys"},
                },
            },
            "input": {
                "type": "object",
                "additionalProperties": False,
                "required": ["owners_before", "fulfillment"],
                "properties": {
                    "owners_before": {"$ref": "#/definitions/public_keys"},
                    "fulfillment": {
                        "anyOf": [
                            {"type": "string", "pattern": "^[a-zA-Z0-9_-]*$"},
                            {"$ref": "#/definitions/condition_details"},
                        ]
                    },
                    "fulfills": {
                        "anyOf": [
                            {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["output_index", "transaction_id"],
                                "properties": {
                                    "output_index": {"$ref": "#/definitions/offset"},
                                    "transaction_id": {
                                        "$ref": "#/definitions/sha3_hexdigest"
                                    },
                                },
                            },
                            {"type": "null"},
                        ]
                    },
                },
            },
            "metadata": {
                "anyOf": [
                    {
                        "type": "object",
                        "additionalProperties": True,
                        "minProperties": 1,
                    },
                    {"type": "null"},
                ]
            },
            "condition_details": {
                "anyOf": [
                    {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["type", "public_key"],
                        "properties": {
                            "type": {
                                "type": "string",
                                "pattern": "^ed25519-sha-256$",
                            },
                            "public_key": {"$ref": "#/definitions/base58"},
                        },
                    },
                    {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["type", "threshold", "subconditions"],
                        "properties": {
                            "type": {
                                "type": "string",
                                "pattern": "^threshold-sha-256$",
                            },
                            "threshold": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 100,
                            },
                            "subconditions": {
                                "type": "array",
                                "items": {
                                    "anyOf": [
                                        {
                                            "type": "object",
                                            "additionalProperties": False,
                                            "required": ["type", "public_key"],
                                            "properties": {
                                                "type": {
                                                    "type": "string",
                                                    "pattern": "^ed25519-sha-256$",
                                                },
                                                "public_key": {
                                                    "$ref": "#/definitions/base58"
                                                },
                                            },
                                        },
                                        {
                                            "type": "object",
                                            "additionalProperties": False,
                                            "required": [
                                                "type",
                                                "threshold",
                                                "subconditions",
                                            ],
                                            "properties": {
                                                "type": {
                                                    "type": "string",
                                                    "pattern": "^threshold-sha-256$",
                                                },
                                                "threshold": {
                                                    "type": "integer",
                                                    "minimum": 1,
                                                    "maximum": 100,
                                                },
                                                "subconditions": {
                                                    "type": "array",
                                                    "items": {
                                                        "anyOf": [
                                                            {
                                                                "type": "object",
                                                                "additionalProperties": False,  # noqa: E501
                                                                "required": [
                                                                    "type",
                                                                    "public_key",
                                                                ],
                                                                "properties": {
                                                                    "type": {
                                                                        "type": "string",  # noqa: E501
                                                                        "pattern": "^ed25519-sha-256$",  # noqa: E501
                                                                    },
                                                                    "public_key": {
                                                                        "$ref": "#/definitions/base58"  # noqa: E501
                                                                    },
                                                                },
                                                            },
                                                            {
                                                                "type": "object",
                                                                "additionalProperties": False,  # noqa: E501
                                                                "required": [
                                                                    "type",
                                                                    "threshold",
                                                                    "subconditions",
                                                                ],
                                                                "properties": {
                                                                    "type": {
                                                                        "type": "string",  # noqa: E501
                                                                        "pattern": "^threshold-sha-256$",  # noqa: E501
                                                                    },
                                                                    "threshold": {
                                                                        "type": "integer",  # noqa: E501
                                                                        "minimum": 1,
                                                                        "maximum": 100,
                                                                    },
                                                                    "subconditions": {
                                                                        "type": "array",
                                                                        "items": {},
                                                                    },
                                                                },
                                                            },
                                                        ]
                                                    },
                                                },
                                            },
                                        },
                                    ]
                                },
                            },
                        },
                    },
                ]
            },
        },
    }

    v2 = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "additionalProperties": False,
        "title": "Transaction Schema",
        "required": [
            "id",
            "inputs",
            "outputs",
            "operation",
            "metadata",
            "asset",
            "version",
        ],
        "properties": {
            "id": {
                "anyOf": [
                    {"$ref": "#/definitions/sha3_hexdigest"},
                    {"type": "null"},
                ]
            },
            "operation": {"$ref": "#/definitions/operation"},
            "asset": {"$ref": "#/definitions/asset"},
            "inputs": {
                "type": "array",
                "title": "Transaction inputs",
                "items": {"$ref": "#/definitions/input"},
            },
            "outputs": {"type": "array", "items": {"$ref": "#/definitions/output"}},
            "metadata": {"$ref": "#/definitions/metadata"},
            "version": {"type": "string", "pattern": "^2\\.0$"},
        },
        "definitions": {
            "offset": {"type": "integer", "minimum": 0},
            "base58": {"pattern": "[1-9a-zA-Z^OIl]{43,44}", "type": "string"},
            "public_keys": {
                "anyOf": [
                    {"type": "array", "items": {"$ref": "#/definitions/base58"}},
                    {"type": "null"},
                ]
            },
            "sha3_hexdigest": {"pattern": "[0-9a-f]{64}", "type": "string"},
            "uuid4": {
                "pattern": "[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}",  # noqa: E501
                "type": "string",
            },
            "operation": {
                "type": "string",
                "enum": [
                    "CREATE",
                    "TRANSFER",
                    "VALIDATOR_ELECTION",
                    "CHAIN_MIGRATION_ELECTION",
                    "VOTE",
                ],
            },
            "asset": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "id": {"$ref": "#/definitions/sha3_hexdigest"},
                    "data": {
                        "anyOf": [
                            {"type": "object", "additionalProperties": True},
                            {"type": "null"},
                        ]
                    },
                },
            },
            "output": {
                "type": "object",
                "additionalProperties": False,
                "required": ["amount", "condition", "public_keys"],
                "properties": {
                    "amount": {"type": "string", "pattern": "^[0-9]{1,20}$"},
                    "condition": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["details", "uri"],
                        "properties": {
                            "details": {"$ref": "#/definitions/condition_details"},
                            "uri": {
                                "type": "string",
                                "pattern": "^ni:///sha-256;([a-zA-Z0-9_-]{0,86})[?](fpt=(ed25519|threshold)-sha-256(&)?|cost=[0-9]+(&)?|subtypes=ed25519-sha-256(&)?){2,3}$",
                            },
                        },
                    },
                    "public_keys": {"$ref": "#/definitions/public_keys"},
                },
            },
            "input": {
                "type": "object",
                "additionalProperties": False,
                "required": ["owners_before", "fulfillment"],
                "properties": {
                    "owners_before": {"$ref": "#/definitions/public_keys"},
                    "fulfillment": {
                        "anyOf": [
                            {"type": "string", "pattern": "^[a-zA-Z0-9_-]*$"},
                            {"$ref": "#/definitions/condition_details"},
                        ]
                    },
                    "fulfills": {
                        "anyOf": [
                            {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["output_index", "transaction_id"],
                                "properties": {
                                    "output_index": {"$ref": "#/definitions/offset"},
                                    "transaction_id": {
                                        "$ref": "#/definitions/sha3_hexdigest"
                                    },
                                },
                            },
                            {"type": "null"},
                        ]
                    },
                },
            },
            "metadata": {
                "anyOf": [
                    {
                        "type": "object",
                        "additionalProperties": True,
                        "minProperties": 1,
                    },
                    {"type": "null"},
                ]
            },
            "condition_details": {
                "anyOf": [
                    {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["type", "public_key"],
                        "properties": {
                            "type": {
                                "type": "string",
                                "pattern": "^ed25519-sha-256$",
                            },
                            "public_key": {"$ref": "#/definitions/base58"},
                        },
                    },
                    {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["type", "threshold", "subconditions"],
                        "properties": {
                            "type": {
                                "type": "string",
                                "pattern": "^threshold-sha-256$",
                            },
                            "threshold": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 100,
                            },
                            "subconditions": {
                                "type": "array",
                                "items": {
                                    "anyOf": [
                                        {
                                            "type": "object",
                                            "additionalProperties": False,
                                            "required": ["type", "public_key"],
                                            "properties": {
                                                "type": {
                                                    "type": "string",
                                                    "pattern": "^ed25519-sha-256$",
                                                },
                                                "public_key": {
                                                    "$ref": "#/definitions/base58"
                                                },
                                            },
                                        },
                                        {
                                            "type": "object",
                                            "additionalProperties": False,
                                            "required": [
                                                "type",
                                                "threshold",
                                                "subconditions",
                                            ],
                                            "properties": {
                                                "type": {
                                                    "type": "string",
                                                    "pattern": "^threshold-sha-256$",
                                                },
                                                "threshold": {
                                                    "type": "integer",
                                                    "minimum": 1,
                                                    "maximum": 100,
                                                },
                                                "subconditions": {
                                                    "type": "array",
                                                    "items": {
                                                        "anyOf": [
                                                            {
                                                                "type": "object",
                                                                "additionalProperties": False,  # noqa: E501
                                                                "required": [
                                                                    "type",
                                                                    "public_key",
                                                                ],
                                                                "properties": {
                                                                    "type": {
                                                                        "type": "string",  # noqa: E501
                                                                        "pattern": "^ed25519-sha-256$",  # noqa: E501
                                                                    },
                                                                    "public_key": {
                                                                        "$ref": "#/definitions/base58"  # noqa: E501
                                                                    },
                                                                },
                                                            },
                                                            {
                                                                "type": "object",
                                                                "additionalProperties": False,  # noqa: E501
                                                                "required": [
                                                                    "type",
                                                                    "threshold",
                                                                    "subconditions",
                                                                ],
                                                                "properties": {
                                                                    "type": {
                                                                        "type": "string",  # noqa: E501
                                                                        "pattern": "^threshold-sha-256$",  # noqa: E501
                                                                    },
                                                                    "threshold": {
                                                                        "type": "integer",  # noqa: E501
                                                                        "minimum": 1,
                                                                        "maximum": 100,
                                                                    },
                                                                    "subconditions": {
                                                                        "type": "array",
                                                                        "items": {},
                                                                    },
                                                                },
                                                            },
                                                        ]
                                                    },
                                                },
                                            },
                                        },
                                    ]
                                },
                            },
                        },
                    },
                ]
            },
        },
    }

    assert not is_subschema(v1, v2)

    assert not is_subschema(v2, v1)


def test_transaction_vote_transaction_validator_election():
    transaction_validator_election = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "title": "Validator Election Schema - Propose a change to validator set",
        "required": ["operation", "asset", "outputs"],
        "properties": {
            "operation": {"type": "string", "value": "VALIDATOR_ELECTION"},
            "asset": {
                "additionalProperties": False,
                "properties": {
                    "data": {
                        "additionalProperties": False,
                        "properties": {
                            "node_id": {"type": "string"},
                            "seed": {"type": "string"},
                            "public_key": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["value", "type"],
                                "properties": {
                                    "value": {"type": "string"},
                                    "type": {
                                        "type": "string",
                                        "enum": [
                                            "ed25519-base16",
                                            "ed25519-base32",
                                            "ed25519-base64",
                                        ],
                                    },
                                },
                            },
                            "power": {"$ref": "#/definitions/positiveInteger"},
                        },
                        "required": ["node_id", "public_key", "power"],
                    }
                },
                "required": ["data"],
            },
            "outputs": {"type": "array", "items": {"$ref": "#/definitions/output"}},
        },
        "definitions": {
            "output": {
                "type": "object",
                "properties": {
                    "condition": {
                        "type": "object",
                        "required": ["uri"],
                        "properties": {
                            "uri": {
                                "type": "string",
                                "pattern": "^ni:///sha-256;([a-zA-Z0-9_-]{0,86})[?](fpt=ed25519-sha-256(&)?|cost=[0-9]+(&)?|subtypes=ed25519-sha-256(&)?){2,3}$",
                            }
                        },
                    }
                },
            },
            "positiveInteger": {"minimum": 0, "type": "integer"},
        },
    }

    transaction_vote = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "title": "Vote Schema - Vote on an election",
        "required": ["operation", "outputs"],
        "properties": {
            "operation": {"type": "string", "value": "VOTE"},
            "outputs": {"type": "array", "items": {"$ref": "#/definitions/output"}},
        },
        "definitions": {
            "output": {
                "type": "object",
                "properties": {
                    "condition": {
                        "type": "object",
                        "required": ["uri"],
                        "properties": {
                            "uri": {
                                "type": "string",
                                "pattern": "^ni:///sha-256;([a-zA-Z0-9_-]{0,86})[?](fpt=ed25519-sha-256(&)?|cost=[0-9]+(&)?|subtypes=ed25519-sha-256(&)?){2,3}$",
                            }
                        },
                    }
                },
            }
        },
    }

    assert is_subschema(transaction_validator_election, transaction_vote)

    assert not is_subschema(transaction_vote, transaction_validator_election)
