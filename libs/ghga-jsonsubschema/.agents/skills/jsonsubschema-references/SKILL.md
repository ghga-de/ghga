---
name: jsonsubschema-references
description: The JSON Schema draft-4 spec, how draft 4 differs from later drafts, and the API pitfalls of the pinned greenery, portion, jsonref and jsonschema versions. Use when unsure about a keyword's semantics or before changing code that calls into these libraries; do not answer from memory.
---

# References for jsonsubschema

This library implements subtype checking for **JSON Schema draft 4 only** (`config.VALIDATOR = jsonschema.Draft4Validator`).
Keyword semantics changed across drafts, so check the draft-4 documents, not the latest spec.

## Draft-4 specification

- Core spec: <https://datatracker.ietf.org/doc/html/draft-zyp-json-schema-04>
- Validation keywords (the one you usually need): <https://datatracker.ietf.org/doc/html/draft-fge-json-schema-validation-00>
- Meta-schema: <https://json-schema.org/draft-04/schema>
- Index of all drafts and their documents: <https://json-schema.org/specification-links>
- Readable explanations, flagging draft differences: <https://json-schema.org/understanding-json-schema/>

The spec defines validation only.
When a keyword's *subtyping* interpretation is unclear, consult `DETAILS.md` and the ISSTA 2021 paper linked in `README.md`.

## Draft 4 against later drafts

Verify against the spec before relying on these, but know they exist:

- `exclusiveMinimum`/`exclusiveMaximum` are **booleans** modifying `minimum`/`maximum` (in draft 6+ they are standalone numbers).
- `const` does **not exist** (added in draft 6); use a single-value `enum`.
- `enum` must be a **non-empty** array per spec.
  This fork deliberately treats an empty `enum` as an uninhabited schema instead of an error.
- Boolean schemas `true`/`false` are **not valid** schemas (draft 6+ only).
- `items` is a schema (applies to all elements) or an **array of schemas** (positional) with `additionalItems` for the rest — no `prefixItems`.
- `$id` is spelled `id`; `$ref` resolution follows draft-4 scoping rules.
- No `propertyNames`, `contains`, `if`/`then`/`else` (all later drafts).
- `required` is an array of property names at the object level.
- `format` is an optional annotation; this library does not decide subtyping on it.

## Pinned dependencies

Version bounds are in `[project.dependencies]` of `pyproject.toml`.

| Library | Used for | Docs |
|---|---|---|
| greenery | regex/DFA operations for string subtyping | <https://github.com/qntm/greenery> (README) |
| portion | numeric interval arithmetic | <https://github.com/AlexandreDecan/portion> (README) |
| jsonref | `$ref` resolution before canonicalization | <https://jsonref.readthedocs.io/> |
| jsonschema | draft-4 validation of inputs and intermediates | <https://python-jsonschema.readthedocs.io/> |

API pitfalls in these pins:

- **greenery** (`>=4.2,<5`): the 4.x API is `from greenery import parse` returning `Pattern` objects; the `lego`/`fsm` modules of 2.x/3.x, common in old examples, no longer exist.
  JSON Schema specifies ECMA-262 regexes for `pattern` and `patternProperties`, but greenery supports only *regular* expressions (no lookaround, no backreferences) — check both when a pattern question comes up.
- **portion** (`>=2.6,<3`): intervals are immutable; build them with `portion.closed/open/openclosed/...` and test emptiness with `.empty`, not with the truthiness of the bounds.
- **jsonref** (`>=1.1,<2`): this code calls `jsonref.JsonRef.replace_refs(...)`; the top-level `replace_refs` function has different laziness defaults, so check before swapping one for the other.
- **jsonschema** (`>=4.26,<5`): only `Draft4Validator` is used (see `config.py`); do not use the newer validator classes for subtyping decisions.

When the docs and the installed version disagree, trust the installed version: read the package source under `.venv/lib/`.
