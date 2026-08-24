---
name: dependency-docs
description: Look up current documentation for this project's dependencies (greenery, portion, jsonref, jsonschema) and dev tools (ruff, mypy, pytest, uv) via Context7 or the official docs. Use before writing or changing code that calls into these libraries — they are niche and have had breaking API changes, so do not rely on memory.
---

# Looking up dependency documentation

## Preferred: Context7

If the Context7 MCP tools are available (load them via ToolSearch:
`resolve-library-id`, `query-docs`), use them first — they return current,
version-aware docs:

1. `resolve-library-id` with the library name (e.g. "greenery", "portion").
2. `query-docs` with a specific question, not just a topic.

Context7 is a claude.ai connector and may be absent in headless/CI runs;
fall back to WebFetch on the official docs below.

## Official docs (WebFetch fallbacks)

Runtime dependencies (version bounds in `[project.dependencies]` of
pyproject.toml; check the installed version with `uv pip list` if in doubt):

| Library | Used for | Docs |
|---|---|---|
| greenery | regex/DFA operations for string subtyping | https://github.com/qntm/greenery (README) |
| portion | numeric interval arithmetic | https://github.com/AlexandreDecan/portion (README) |
| jsonref | `$ref` resolution before canonicalization | https://jsonref.readthedocs.io/ |
| jsonschema | draft-4 validation of inputs/intermediates | https://python-jsonschema.readthedocs.io/ |

Dev tooling:

- ruff: https://docs.astral.sh/ruff/ (rule codes: https://docs.astral.sh/ruff/rules/)
- uv: https://docs.astral.sh/uv/
- pytest: https://docs.pytest.org/
- mypy: https://mypy.readthedocs.io/

## Known API pitfalls in this codebase's pins

- **greenery** (pinned `>=4.2,<5`): the 4.x API is `from greenery import
  parse` returning `Pattern` objects — the older `lego`/`fsm` module layout
  from 2.x/3.x found in old examples and training data does not exist
  anymore. greenery supports only *regular* regexes (no lookaround, no
  backreferences).
- **portion** (pinned `>=2.6,<3`): intervals are immutable; construction via
  `portion.closed/open/openclosed/...`, and emptiness is checked with
  `.empty`, not truthiness of bounds.
- **jsonref** (pinned `>=1.1,<2`): this codebase calls
  `jsonref.JsonRef.replace_refs(...)`; the 1.x top-level `replace_refs`
  function has different laziness defaults — don't swap one for the other
  without checking.
- **jsonschema** (pinned `>=4.26,<5`): only `Draft4Validator` is used here
  (see `config.py`); newer validator classes exist but must not be used for
  subtyping decisions.

If docs and the installed version disagree, trust the installed version:
`uv run python -c "import greenery; help(greenery.parse)"` or read the
package source under `.venv/`.
