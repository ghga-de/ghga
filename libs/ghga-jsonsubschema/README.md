[![PyPI version shields.io](https://img.shields.io/pypi/v/ghga-jsonsubschema.svg)](https://pypi.org/project/ghga-jsonsubschema/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/ghga-jsonsubschema.svg)](https://pypi.org/project/ghga-jsonsubschema/)

# GHGA JSON Subschema

> **Note:** This is a fork of [IBM/jsonsubschema](https://github.com/ibm/jsonsubschema) maintained by the [German Human Genome-Phenome Archive (GHGA)](https://www.ghga.de/). It was created to bring in necessary fixes, updates, and functionality required by GHGA-related projects.

**ghga-jsonsubschema** checks if one JSON schema is a subschema (subtype) of another.

For any two JSON schemas s1 and s2, s1 <: s2 (reads s1 is subschema/subtype of s2) if every JSON document instance that validates against s1 also validates against s2.

jsonsubschema is very useful in analysing schema evolution and ensuring that newer schema versions are backward compatible.
jsonsubschema also enables static type checking on different components of a system that uses JSON schema to describe data interfaces among the system's different components.

For a practical overview of the architecture, purpose, and usage of this library, please see [DETAILS.md](https://github.com/ghga-de/ghga/blob/main/libs/ghga-jsonsubschema/DETAILS.md). For the formal foundations and deep technical details, please refer to the [ISSTA 2021 paper](https://dl.acm.org/doi/10.1145/3460319.3464796) by Andrew Habib, Avraham Shinnar, Martin Hirzel, and Michael Pradel, the original authors of this library.

## Installation

### Requirements

* Python 3.13+

### Install from PyPI

```sh
pip install ghga-jsonsubschema
```

### Install from source

```sh
git clone https://github.com/ghga-de/ghga.git
cd ghga
uv sync
```

## Running subschema

JSON subschema provides two usage interfaces:

### CLI interface

First, create two JSON schema examples by executing the following:

```sh
echo '{"type": ["null", "string"]}' > s1.json
echo '{"type": ["string", "null"], "not": {"enum": [""]}}' > s2.json
```

Then, invoke the CLI by executing:

```sh
python -m jsonsubschema s2.json s1.json
```

### Python API

```python
from jsonsubschema import is_subschema

def main():
    s1 = {'type': "integer"}
    s2 = {'type': ["integer", "string"]}

    print(f'LHS <: RHS {is_subschema(s1, s2)}')

if __name__ == "__main__":
    main()
```

## Development

This package is a member of the [GHGA monorepo](https://github.com/ghga-de/ghga) and is
developed from the repository root rather than on its own. The repository ships a
devcontainer with the whole toolchain: open it in VS Code and run
`Remote-Containers: Reopen in Container`, or set the environment up directly with
`just sync`.

The usual tasks, run from the repository root (see
[ADR-0015](https://github.com/ghga-de/ghga/blob/main/docs/adr/0015-task-runner.md) for the
full recipe list):

```bash
just sync                          # install every member plus the shared dev toolchain
just test libs/ghga-jsonsubschema  # this member's test suite
just lint                          # ruff check + format check across the workspace
```

## Changes made by GHGA

This fork is based on version 0.0.8 of [IBM/jsonsubschema](https://github.com/ibm/jsonsubschema) and introduces additional changes:

* Public API names have been changed to align with PEP 8.
* The minimum required Python version is now 3.13.
* Packaging uses more modern conventions.
* Tests have been converted from `unittest` to `pytest`.
* An empty `enum` is now treated as an uninhabited schema.
* Bugs inherited from upstream have been fixed: negating a numeric schema now
  respects `exclusiveMinimum`/`exclusiveMaximum`, intersecting numeric schemas
  no longer drops exclusive bounds, nested `anyOf` unions are now fully
  flattened (previously, adjacent nested unions could make two equivalent
  schemas compare as unrelated), and arrays with at most one item are now
  recognized as satisfying `uniqueItems`.
* The `dependencies` keyword (which upstream silently ignores) now raises
  `exceptions.UnsupportedDependencies` instead of potentially returning
  unsound verdicts.
* Negating an integer schema (e.g.
  `{"not": {"type": "integer", "minimum": 10, "maximum": 20}}`) now yields
  the exact complement — including the non-integer numbers, represented
  internally as `{"type": "number", "not": {"multipleOf": 1}}` — where
  upstream silently computes a too-small complement that can yield unsound
  verdicts. Only negating a numeric schema with a non-trivial `multipleOf`
  (whose complement would contain the non-multiples) raises
  `exceptions.UnsupportedNegatedNumeric` instead of returning potentially
  wrong results.
* Uninhabited numeric schemas whose `multipleOf` has no multiple within the
  schema's bounds are now recognized as such, and subtype checks of numeric
  schemas admitting a single value are now exact (e.g.
  `{"type": "integer"}` is now a subschema of
  `{"type": "number", "multipleOf": 0.5}`).

## License

This repository is distributed under the terms of the Apache 2.0 License, see [LICENSE.txt](https://github.com/ghga-de/ghga/blob/main/libs/ghga-jsonsubschema/LICENSE.txt).
