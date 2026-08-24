# AGENTS.md

Guidance for AI coding agents working in this repository.

## What this project is

**ghga-jsonsubschema** is a Python library that decides whether one JSON schema
is a *subschema* (subtype) of another: `s1 <: s2` holds if every JSON document
that validates against `s1` also validates against `s2`. It is a fork of
[IBM/jsonsubschema](https://github.com/ibm/jsonsubschema) maintained by the
[German Human Genome-Phenome Archive (GHGA)](https://www.ghga.de/), created to
bring in fixes, updates, and functionality required by GHGA projects.

Read [README.md](README.md) for usage and [DETAILS.md](DETAILS.md) for an
overview of the theory (canonicalization → simplification → subtype checking).
The formal foundations are described in the ISSTA 2021 paper "Finding Data
Compatibility Bugs with JSON Subschema Checking".

Key facts:

- Package name on PyPI: `ghga-jsonsubschema`; import name: `jsonsubschema`.
- Requires Python 3.10+; dependency management with `uv` (`uv.lock`).
- Only JSON Schema **draft 4** is supported (`config.VALIDATOR`).
- Recursive `$ref`s, some negated object/array/numeric schemas, the
  `dependencies` keyword, and non-regular regexes are *unsupported* and raise
  dedicated exceptions rather than returning wrong answers.

## Repository layout

```
src/jsonsubschema/
├── __init__.py          # Public exports (the only supported import surface)
├── api.py               # is_subschema, is_equivalent, meet_schemas, join_schemas
├── cli.py               # `jsonsubschema LHS.json RHS.json` CLI (also python -m jsonsubschema)
├── config.py            # Global flags: set_debug, set_warn_uninhabited, validator draft
├── exceptions.py        # Unsupported-case exceptions (recursive refs, negated objects/arrays, ...)
├── _canonicalization.py # Step 1+2: canonicalize and simplify schemas, embed checkers
├── _checkers.py         # Step 3: JSONschema class hierarchy with meet/join/subtype per JSON type
├── _constants.py        # JSON type/keyword constants
└── _utils.py            # Validation, regex/interval helpers, debug printing
tests/                   # pytest suite, one file per JSON type/feature area
.github/workflows/       # lint.yaml (ruff+mypy), test.yaml (pytest on 3.10-3.13), publish.yaml
```

Modules prefixed with `_` are internal; everything meant for users is
re-exported in `__init__.py.__all__`. Do not add new public API without
updating `__init__.py` and the README.

### Core architecture (the 3-step pipeline)

1. **Canonicalization** (`_canonicalization.py`): splits mixed `type` lists
   into `anyOf`, makes defaults explicit, rewrites booleans as enums,
   integers as `number` + `multipleOf: 1`, string length bounds as regexes.
2. **Simplification** (`_canonicalization.py`): eliminates `enum`, `not`,
   `allOf`, `anyOf`, `oneOf` where possible, approaching a disjunctive
   normal form, and *embeds checkers* — plain dicts become `JSONschema`
   subclass instances from `_checkers.py`.
3. **Subtype checking** (`_checkers.py`): type-homogeneous fragments are
   compared with per-type logic (intervals via `portion` for numbers,
   regex/DFA operations via `greenery` for strings, structural rules for
   objects/arrays). `meet` = schema intersection, `join` = union.

## Development workflow

```sh
uv sync --extra dev            # set up environment
uv run pre-commit install      # install git hooks (once)
uv run pytest tests/           # run test suite
uv run pytest --cov tests/     # with coverage
uv run ruff check .            # lint
uv run ruff format .           # format
uv run mypy src tests          # type check (pre-commit passes --no-warn-unused-ignores)
uv run pre-commit run --all-files   # everything the CI lint job runs
```

CI runs the test suite on Python 3.10 through 3.13 on every push, so changes
must work across that range. Direct commits to `main` are blocked by a
pre-commit hook; work on feature branches.

## Coding conventions

- **Formatting/linting**: ruff with an extensive rule set (see
  `[tool.ruff.lint]` in [pyproject.toml](pyproject.toml)), line length 88,
  target py313. Run `ruff check` and `ruff format` before committing —
  pre-commit enforces both. Max McCabe complexity is 10; prefer extracting
  helpers over adding `noqa` suppressions.
- **Docstrings**: pydocstyle PEP 257 convention is enforced for all public
  and private functions/classes in `src/` (tests are exempt from D101–D103).
- **Use `is_top()` / `is_bot()` to test schema-valued slots in
  `_checkers.py`.** Keywords like `additionalProperties`/`additionalItems`
  may hold a Python bool *or* a checker object (`JSONtop()`/`JSONbot()`/any
  `JSONschema`), so never compare them with `is True`/`is False` or
  truthiness (`JSONtop() is not True`, and `__bool__` is overridden) —
  call the `is_top`/`is_bot` helpers instead.
- **`JSONschema` subclasses `dict`.** Checker objects are dictionaries with
  behavior; mutating keys changes the schema. `UninhabitedMeta` runs
  validation and uninhabited-checks on every construction — invalid
  intermediate states raise immediately.
- **File headers**: source files keep the original attribution header
  (`Originally created ... by Andrew Habib. Contains changes by The GHGA
  Authors. SPDX-License-Identifier: Apache-2.0`). Keep it when editing;
  use the same style (without the attribution line) for new files.
- **`__all__`**: every module declares `__all__`; keep it sorted (RUF022)
  and updated when adding/removing names.
- **Naming**: PEP 8 throughout. This fork deliberately renamed the upstream
  camelCase API (e.g. upstream `isSubschema` → `is_subschema`,
  `canonicalizeSchema` → `canonicalize_schema`). Keep new names PEP 8.
- **Unsupported features fail loudly**: when the algorithm cannot decide a
  case, raise one of the `exceptions.py` exceptions — never silently return
  `True`/`False`.

## Testing conventions

- Plain pytest: module-level `test_*` functions with bare `assert`
  statements, no test classes and no unittest idioms (the suite was
  converted from unittest — do not reintroduce it).
- Tests are organized by JSON type/feature: `test_string.py`,
  `test_numeric.py`, `test_object.py`, `test_array.py`, `test_refs.py`, etc.
  Put new tests in the matching file.
- The typical test builds two inline schema dicts and asserts
  `is_subschema` / `is_equivalent` in both directions:

  ```python
  def test_min_min():
      s1 = {"type": "string", "minLength": 5}
      s2 = {"type": "string", "maxLength": 1}
      assert not is_subschema(s1, s2)
      assert not is_subschema(s2, s1)
  ```

- `test_from_lale.py` and `test_ai_subschema.py` are large generated/imported
  regression suites — don't edit them by hand except to fix genuine breakage.

## Fork maintenance

Upstream is [IBM/jsonsubschema](https://github.com/ibm/jsonsubschema); this
fork is based on its version 0.0.8 (released June 2026). When porting
upstream changes,
translate the camelCase API names to the PEP 8 names used here and adapt to
pytest-style tests. GHGA-specific behavior changes (e.g. an empty `enum` is
treated as uninhabited) are listed in the README section "Changes made by
GHGA" — keep that list up to date when the fork diverges further.

## Repo-specific pitfalls

- `.gitignore` ignores `*.json` globally (test fixtures are inline dicts, not
  JSON files). If you create sample schema files for manual testing, put them
  in a scratch directory outside the repo or expect git to ignore them.
- The `.dev/` directory is a local, untracked scratch area for development
  notes; never rely on it in code or CI.
- Debug output is toggled globally via `jsonsubschema.set_debug(True)`
  (prints intermediate canonical forms) — remember to leave it off in tests.
