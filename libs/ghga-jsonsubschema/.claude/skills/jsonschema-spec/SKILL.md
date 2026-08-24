---
name: jsonschema-spec
description: Look up authoritative JSON Schema specification documentation, especially draft 4 (the only draft this library supports). Use when unsure about the exact semantics of a schema keyword, validation rule, or draft differences — do not answer spec questions from memory.
---

# Looking up the JSON Schema specification

This library implements subtype checking for **JSON Schema draft 4 only**
(`config.VALIDATOR = jsonschema.Draft4Validator`). Keyword semantics changed
across drafts, so always check the draft-4 documents, not the latest spec.

## Authoritative draft-4 sources (WebFetch these)

- Core spec: https://datatracker.ietf.org/doc/html/draft-zyp-json-schema-04
- Validation keywords (the one you usually need):
  https://datatracker.ietf.org/doc/html/draft-fge-json-schema-validation-00
- Meta-schema: https://json-schema.org/draft-04/schema
- Index of all drafts and their documents:
  https://json-schema.org/specification-links

For readable explanations (covers modern drafts, flags draft differences):
https://json-schema.org/understanding-json-schema/

## Draft-4 semantics that differ from later drafts

Verify against the spec before relying on these, but know they exist:

- `exclusiveMinimum`/`exclusiveMaximum` are **booleans** modifying
  `minimum`/`maximum` (in draft 6+ they are standalone numbers).
- `const` does **not exist** (added in draft 6); use single-value `enum`.
- `enum` must be a **non-empty** array per spec. (This fork deliberately
  treats an empty `enum` as an uninhabited schema instead of an error.)
- Boolean schemas `true`/`false` are **not valid** schemas (draft 6+ only).
- `items` can be a schema (applies to all elements) or an **array of
  schemas** (tuple validation, positional) with `additionalItems` for the
  rest — no `prefixItems`.
- `$id` is spelled `id`; `$ref` resolution follows draft-4 scoping rules.
- No `propertyNames`, `contains`, `if`/`then`/`else` (all later drafts).
- `required` is an array of property names at the object level.
- `format` is an optional annotation; this library does not decide subtyping
  based on `format`.

## Related lookups

- Python `jsonschema` library behavior (used for validation here):
  https://python-jsonschema.readthedocs.io/ — or use the Context7 tools
  (`resolve-library-id` / `query-docs`) if available.
- Regex semantics for `pattern`/`patternProperties`: JSON Schema specifies
  ECMA-262 regexes, but this library compiles patterns with
  [greenery](https://github.com/qntm/greenery), which supports only
  *regular* expressions (no lookaround/backreferences) — check both when a
  pattern question comes up.
- When a keyword's *subtyping* interpretation is unclear (spec only defines
  validation), consult DETAILS.md and the ISSTA 2021 paper linked in
  README.md.
