<!-- rumdl-disable MD013 -->
[![PyPI version shields.io](https://img.shields.io/pypi/v/ghga-arcticfreeze.svg)](https://pypi.org/project/ghga-arcticfreeze/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/ghga-arcticfreeze.svg)](https://pypi.org/project/ghga-arcticfreeze/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
<!-- rumdl-enable MD013 -->

# arcticfreeze

> **Note:** This is a fork of [KerstenBreuer/arcticfreeze](https://github.com/KerstenBreuer/arcticfreeze) maintained by the [German Human Genome-Phenome Archive (GHGA)](https://www.ghga.de/).
> It was created to bring in fixes and updates required by GHGA-related projects.
> Many thanks to Kersten Breuer for the initial implementation.
> The distribution is published as `ghga-arcticfreeze`, but the import path remains `arcticfreeze`, so it is a drop-in replacement for the upstream package.

Enjoy Python on the rocks with deeply (recursively) frozen data structures.

## Description

Python's built-in immutable types only go one level deep: a `tuple` may still contain a `list`, and a `frozenset` cannot contain a `dict` at all.
**arcticfreeze** closes that gap by recursively converting a nested data structure into an immutable counterpart.

It provides:

- **`freeze`** – a function that deep freezes an arbitrary object.
  It walks the object tree bottom-up and replaces every mutable container with an immutable equivalent (`list`/`deque` → `tuple`, `dict` → `FrozenDict`, `set` → `frozenset`), leaving already-immutable values untouched.
- **`FrozenDict`** – a hashable, immutable `Mapping` (built on [immutabledict](https://pypi.org/project/immutabledict/)) with first-class type-hint support and out-of-the-box Pydantic v2 integration (validation, JSON schema, and serialization).
- **`Converter`** – an extension point for teaching `freeze` how to handle your own types, including a priority mechanism to override the standard converters.

Freezing is useful wherever shared data must not be mutated by accident: configuration objects, cached values, dictionary keys, or any value that should be hashable and safe to pass around.

## Installation

### Requirements

- Python 3.11+

### Install from PyPI

```sh
pip install ghga-arcticfreeze
```

To use the `FrozenDict` type within Pydantic models, install the optional `pydantic` extra:

```sh
pip install "ghga-arcticfreeze[pydantic]"
```

## Usage

### Deep freezing

```python
from arcticfreeze import FrozenDict, freeze

original = {"a": [1, 2, {"b": {"c", "d"}}]}
frozen = freeze(original)

# The nested list became a tuple, the nested dicts became FrozenDicts,
# and the nested set became a frozenset:
assert frozen == FrozenDict({"a": (1, 2, FrozenDict({"b": frozenset({"c", "d"})}))})

# The result is hashable and cannot be modified:
hash(frozen)
```

Custom types are supported by providing additional converters:

```python
from arcticfreeze import Converter, freeze


class Point:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y


point_converter = Converter(
    input_type=Point,
    convert=lambda obj, freeze_child: (freeze_child(obj.x), freeze_child(obj.y)),
)

assert freeze(Point(1, 2), add_converters=[point_converter]) == (1, 2)
```

A converter must freeze the children of its object with the `freeze_child` callable it gets, not with `freeze`: the depth limit, sharing and cycle detection rely on it.
A custom converter for a type that already has a standard converter replaces it, whatever their priorities.
The priorities decide which converter is used when matching by superclass (`by_superclass=True`).

### Untrusted input

`freeze` is safe to run on data from an untrusted source, such as a parsed request body:

- **Depth:** `max_depth` (default `DEFAULT_MAX_DEPTH`, 100) bounds the nesting depth, where the children of the root object are at depth 1.
  A deeper object raises `MaxDepthExceededError` instead of exhausting the call stack.
  `max_depth=None` turns the bound off and is meant for trusted input only.
  The walk then stops at the recursion limit with `MaxDepthExceededError` as well, but shared objects can build a result nested deeper than that.
- **Cycles:** an object that contains itself raises `ReferenceCycleError`.
- **Shared objects:** an object that occurs several times, as YAML aliases produce, is frozen only once, and all occurrences share the result.
  Each occurrence still counts at its own depth, so sharing cannot build a result nested deeper than `max_depth`.

All errors subclass `FreezeError`, a `ValueError`, so Pydantic reports them as validation errors when `freeze` runs in a validator:

```python
from typing import Annotated, Any

from arcticfreeze import freeze
from pydantic import BaseModel, BeforeValidator


class Document(BaseModel):
    content: Annotated[Any, BeforeValidator(freeze)]
```

### FrozenDict in Pydantic models

```python
from arcticfreeze import FrozenDict
from pydantic import BaseModel


class Config(BaseModel):
    parameters: FrozenDict[str, int]


config = Config(parameters={"a": 1})

# The mapping is validated and converted into a FrozenDict:
assert isinstance(config.parameters, FrozenDict)

# It serializes to a plain dict in JSON mode and stays a FrozenDict in Python mode:
assert config.model_dump(mode="json") == {"parameters": {"a": 1}}
assert isinstance(config.model_dump()["parameters"], FrozenDict)
```

## Development

This package is a member of the [GHGA monorepo](https://github.com/ghga-de/ghga) and is developed from the repository root rather than on its own.
The repository ships a devcontainer with the whole toolchain: open it in VS Code and run `Remote-Containers: Reopen in Container`, or set the environment up directly with `just sync`.

The usual tasks, run from the repository root (see [ADR-0034](https://github.com/ghga-de/ghga/blob/main/docs/adrs/adr-0034-task-runner.md) for the full recipe list):

```bash
just sync                         # install every member plus the shared dev toolchain
just test libs/ghga-arcticfreeze  # this member's test suite
just lint                         # ruff check + format check across the workspace
```

## License

This repository is free to use and modify according to the [Apache 2.0 License](https://github.com/ghga-de/ghga/blob/main/libs/ghga-arcticfreeze/LICENSE).
