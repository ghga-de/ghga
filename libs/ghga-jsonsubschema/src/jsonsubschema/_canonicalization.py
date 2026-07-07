"""JSON Schema canonicalization and simplification.

Originally created on June 24, 2019 by Andrew Habib.
Contains changes by The GHGA Authors.
SPDX-License-Identifier: Apache-2.0
"""

import copy
import math
import re

import jsonsubschema._constants as definitions
import jsonsubschema._utils as utils
from jsonsubschema._checkers import (
    JSONbot,
    JSONtop,
    bool_to_constructor,
    type_to_constructor,
)
from jsonsubschema.exceptions import (
    UnsupportedDependencies,
    UnsupportedEnumCanonicalization,
)

_nan = float("nan")
BOT: dict = {"not": {}}


def canonicalize_schema(obj):
    """Validate and rewrite ``obj`` into an equivalent canonical JSON schema."""
    # {"enum": []} is uninhabited; intercept before validate_schema rejects it
    if utils.is_dict(obj) and obj.get("enum") == []:
        return BOT

    # First, make sure the given json is a valid json schema;
    # this throws jsonschema.SchemaError on unknown types.
    utils.validate_schema(obj)

    # Second, canonicalize the schema.
    if utils.is_dict(obj):
        canonical_schema = canonicalize_dict(obj)

    # Finally, ensure that the canonicalized schema is still a valid json schema.
    utils.validate_schema(canonical_schema)

    return canonical_schema


def canonicalize_dict(d, outer_key=None):  # noqa: C901, PLR0911
    """Canonicalize a schema given as a dict, dispatching on its keywords.

    ``outer_key`` is the key under which ``d`` appears in its parent schema;
    it is used to leave dict containers such as ``properties`` untouched.
    """
    # Not strictly needed, but return these trivial schemas unchanged
    # so that tests of the canonicalization work properly.
    if d in ({}, {"not": {}}):
        return d

    # In draft 4, any validation keyword alongside a $ref is ignored;
    # jsonref's ref resolution (which runs before canonicalization)
    # already drops such siblings, so no handling is needed here.

    # Skip normal dict canonicalization for the contents of properties,
    # patternProperties and dependencies: these are usual dict containers
    # mapping keys to schemas, not schemas themselves.
    if outer_key in ["properties", "patternProperties"]:
        for k, v in d.items():
            d[k] = canonicalize_dict(v)
        return d
    if outer_key == "dependencies":
        for k, v in d.items():
            if utils.is_dict(v):
                d[k] = canonicalize_dict(v)
        return d

    # here, start dict canonicalization
    if not definitions.Jkeywords.intersection(d.keys()):
        return d

    t = d.get("type")
    has_connectors = definitions.Jconnectors.intersection(d.keys())

    # Start canonicalization. Don't modify original dict.
    d = copy.deepcopy(d)

    if has_connectors:
        return canonicalize_connectors(d)
    if "enum" in d:
        return canonicalize_enum(d)
    if "const" in d:
        return canonicalize_const(d)
    if utils.is_str(t):
        return canonicalize_single_type(d)
    if utils.is_list(t):
        return canonicalize_list_of_types(d)
    d["type"] = sorted(definitions.Jtypes)
    return canonicalize_list_of_types(d)


def _is_relevant_keyword(k, t):
    """Return whether keyword ``k`` is relevant for a schema of type ``t``."""
    return (
        k in definitions.Jcommonkw
        or k in definitions.JtypesToKeywords.get(t, set())
        or k in definitions.JNonValidation
    )


def _canonicalize_keywords(d, t):
    """Drop irrelevant keywords of ``d`` in place and canonicalize the rest.

    Returns ``False`` if the ``enum`` admits no value of type ``t``,
    which renders the schema uninhabited.
    """
    for k, v in list(d.items()):
        if not _is_relevant_keyword(k, t):
            d.pop(k)
        elif utils.is_dict(v):
            d[k] = canonicalize_dict(v, k)
        elif utils.is_list(v):
            if k == "enum":
                v = utils.get_typed_enum_vals(v, t)
                if not v:
                    return False
                d[k] = v
            elif k == "required":
                d[k] = sorted(set(v))
            else:
                # "list" must be operand of boolean connectors
                d[k] = [canonicalize_dict(i) for i in v]
    return True


def canonicalize_single_type(d):
    """Canonicalize a schema with a single ``type``, dropping irrelevant keywords."""
    t = d.get("type")
    if t not in definitions.Jtypes:
        # cannot happen: the jsonschema validation at the start rejects unknown types
        raise ValueError(f"Unknown schema type {t!r} at: {d}")
    if t == "object" and d.get("dependencies"):
        # fail loudly instead of ignoring the constraint and potentially
        # returning an unsound verdict
        raise UnsupportedDependencies(schema=d)
    if not _canonicalize_keywords(d, t):
        # no enum value fits the type, so the schema is uninhabited
        return BOT
    if "enum" in d:
        return rewrite_enum(d)
    return d


def canonicalize_list_of_types(d):
    """Canonicalize a schema with a list of ``type`` values into an ``anyOf``."""
    schema_types = set(d.get("type"))
    if schema_types == definitions.JallTypes and not set(d.keys()).intersection(
        definitions.JtypesRestrictionKeywords
    ):
        return JSONtop()

    any_of_schemas = []
    for schema_type in schema_types:
        typed_schema = copy.deepcopy(d)
        typed_schema["type"] = schema_type
        any_of_schemas.append(canonicalize_single_type(typed_schema))

    return {"anyOf": any_of_schemas}


def canonicalize_enum(d):
    """Canonicalize an ``enum`` schema, keeping only values valid against ``d``."""
    valid_vals = utils.get_valid_enum_vals(d["enum"], d)
    if not valid_vals:
        return BOT

    d["enum"] = valid_vals
    actual_t = sorted(
        t
        for i in d.get("enum", [])
        if (t := definitions.PyTypesToJtypes.get(type(i))) is not None
    )
    if "type" in d:
        orig_t = d["type"]
        orig_t = {orig_t} if utils.is_str(orig_t) else set(orig_t)
        d["type"] = orig_t.intersection(actual_t)
    else:
        d["type"] = actual_t
    return canonicalize_list_of_types(d)


def canonicalize_const(d):
    """Canonicalize a ``const`` schema by rewriting it as a single-value ``enum``."""
    d["enum"] = [d.pop("const")]
    return canonicalize_enum(d)


def canonicalize_connectors(d):
    """Canonicalize a schema built from boolean connectors.

    The connectors are ``anyOf``/``allOf``/``oneOf``/``not``. A ``oneOf`` is
    rewritten in terms of ``anyOf``/``allOf``/``not``, and a
    connector combined with other keywords is first split into an ``allOf``.
    """
    connectors = definitions.Jconnectors.intersection(d.keys())
    lhs_kw = definitions.Jkeywords.intersection(d.keys())
    lhs_kw_without_connectors = lhs_kw.difference(connectors)

    # Single connector.
    if len(connectors) == 1 and not lhs_kw_without_connectors:
        connector = connectors.pop()

        if connector == "not":
            d["not"] = canonicalize_dict(d["not"])
            return canonicalize_not(d)

        if connector == "oneOf":
            if len(d[connector]) == 1:
                return canonicalize_dict(d[connector].pop())
            any_of_schemas = []
            for index in range(len(d[connector])):
                selected_schema = [d[connector][index]]
                negated_others = [
                    {"not": schema} for schema in d[connector][:index]
                ] + [{"not": schema} for schema in d[connector][index + 1 :]]
                all_of_schemas = selected_schema + negated_others
                any_of_schemas.append({"allOf": all_of_schemas})
            return canonicalize_connectors({"anyOf": any_of_schemas})

        # Here, the connector is either allOf or oneOf
        # So we better simplify them before proceeding more.
        d[connector] = [canonicalize_dict(schema) for schema in d[connector]]
        return simplify_schema_and_embed_checkers(d)

    # Connector + other keywords. Combine them first.
    all_of_schemas = []
    for connector in connectors:
        all_of_schemas.append(canonicalize_dict({connector: d[connector]}))
        del d[connector]
    if lhs_kw_without_connectors:
        all_of_schemas.append(
            canonicalize_dict({k: d[k] for k in lhs_kw_without_connectors})
        )
    return {"allOf": all_of_schemas}


def canonicalize_not(d):
    """Canonicalize a negated (``not``) schema by pushing the negation inward.

    Double negations cancel and De Morgan's laws turn negated connectors into
    the dual connector of negated operands.
    """
    # d: {} has a 'not' schema
    negated_schema = d["not"]

    t = negated_schema.get("type")

    if t in definitions.Jtypes:
        return d

    if not definitions.Jkeywords.intersection(negated_schema.keys()):
        # The negated schema has no validating keywords, so it accepts
        # every document and its negation is uninhabited.
        return BOT

    connectors = definitions.Jconnectors.intersection(negated_schema.keys())
    if len(connectors) == 1:
        connector = connectors.pop()
        # Case "not: {"not": {...}}
        # Return positive schema (2 nots cancel each other)
        if connector == "not":
            return negated_schema["not"]

        if connector == "anyOf":
            all_of_schemas = [
                canonicalize_not({"not": schema}) for schema in negated_schema["anyOf"]
            ]
            return {"allOf": all_of_schemas}

        # allOf/oneOf: rewrite the connector first, then push the negation
        # into the result.
        return canonicalize_not({"not": canonicalize_connectors(negated_schema)})

    # cannot happen: the negated schema was canonicalized before, which
    # yields either a typed schema or a single boolean connector
    raise ValueError(f"Cannot negate the canonicalized schema: {negated_schema}")


def rewrite_enum(d):
    """Rewrite a typed ``enum`` schema into range/pattern constraints per value.

    Array and object enums are not supported and raise
    :class:`UnsupportedEnumCanonicalization`.
    """
    t = d.get("type")
    enum = d.get("enum")

    match t:
        case "string":
            pattern = "|".join(f"^{re.escape(str(x))}$" for x in enum)
            ret: dict = {"type": "string", "pattern": pattern}
        case "integer":
            ret = {
                "anyOf": [{"type": "integer", "minimum": i, "maximum": i} for i in enum]
            }
        case "number":
            items = []
            for i in enum:
                if utils.is_int_equiv(i):
                    items.append({"type": "integer", "minimum": i, "maximum": i})
                elif math.isnan(i):
                    items.append({"type": "number", "enum": [_nan]})
                else:
                    items.append({"type": "number", "minimum": i, "maximum": i})
            ret = {"anyOf": items}
        case "boolean":
            return d
        case "null":
            return {"type": "null"}
        case "array" | "object":
            raise UnsupportedEnumCanonicalization(tau=t, schema=d)
        case _:
            return None

    ret["enum"] = enum
    return ret


def simplify_schema_and_embed_checkers(s):  # noqa: C901, PLR0911, PLR0912
    """This function assumes the schema s is already canonicalized.
    So it must be a dict
    """
    if s == {} or not definitions.Jkeywords.intersection(s.keys()):
        return JSONtop()
    if "not" in s and s["not"] == {}:
        return JSONbot()

    # json.array specific
    if "items" in s:
        if utils.is_dict(s["items"]):
            s["items"] = simplify_schema_and_embed_checkers(s["items"])
        elif utils.is_list(s["items"]):
            s["items"] = [simplify_schema_and_embed_checkers(i) for i in s["items"]]

    if "additionalItems" in s and utils.is_dict(s["additionalItems"]):
        s["additionalItems"] = simplify_schema_and_embed_checkers(s["additionalItems"])

    # json.object specific
    if "properties" in s:
        s["properties"] = {
            k: simplify_schema_and_embed_checkers(v) for k, v in s["properties"].items()
        }

    if "patternProperties" in s:
        s["patternProperties"] = {
            k: simplify_schema_and_embed_checkers(v)
            for k, v in s["patternProperties"].items()
        }

    if "additionalProperties" in s and utils.is_dict(s["additionalProperties"]):
        s["additionalProperties"] = simplify_schema_and_embed_checkers(
            s["additionalProperties"]
        )

    if "type" in s:
        return type_to_constructor[s["type"]](s)

    if "not" in s:
        return type_to_constructor[s["not"]["type"]].neg(s["not"])

    if "anyOf" in s:
        anyofs = [simplify_schema_and_embed_checkers(i) for i in s["anyOf"]]
        return bool_to_constructor["anyOf"]({"anyOf": anyofs})

    if "allOf" in s:
        allofs = [simplify_schema_and_embed_checkers(i) for i in s["allOf"]]
        return bool_to_constructor["allOf"]({"allOf": allofs})
    return None
