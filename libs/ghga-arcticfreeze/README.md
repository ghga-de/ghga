[![tests](https://github.com/ghga-de/ghga-arcticfreeze/actions/workflows/tests.yaml/badge.svg)](https://github.com/ghga-de/ghga-arcticfreeze/actions/workflows/tests.yaml)

# arcticfreeze

> **Note:** This is a fork of [KerstenBreuer/arcticfreeze](https://github.com/KerstenBreuer/arcticfreeze)
> maintained by the [German Human Genome-Phenome Archive (GHGA)](https://www.ghga.de/).
> It was created to bring in fixes and updates required by GHGA-related projects.
> Many thanks to Kersten Breuer for the initial implementation.
> The distribution is published as `ghga-arcticfreeze`, but the import path remains
> `arcticfreeze`, so it is a drop-in replacement for the upstream package.

Enjoy Python on the rocks with deeply (recursively) frozen data structures.

## Description

Python's built-in immutable types only go one level deep: a `tuple` may still contain a
`list`, and a `frozenset` cannot contain a `dict` at all. **arcticfreeze** closes that
gap by recursively converting a nested data structure into an immutable counterpart.

It provides:

- **`freeze`** – a function that deep freezes an arbitrary object. It walks the object
  tree bottom-up and replaces every mutable container with an immutable equivalent
  (`list`/`deque` → `tuple`, `dict` → `FrozenDict`, `set` → `frozenset`), leaving
  already-immutable values untouched.
- **`FrozenDict`** – a hashable, immutable `Mapping` (built on
  [immutabledict](https://pypi.org/project/immutabledict/)) with first-class type-hint
  support and out-of-the-box Pydantic v2 integration (validation, JSON schema, and
  serialization).
- **`Converter`** – an extension point for teaching `freeze` how to handle your own
  types, including a priority mechanism to override the standard converters.

Freezing is useful wherever shared data must not be mutated by accident: configuration
objects, cached values, dictionary keys, or any value that should be hashable and safe
to pass around.

## Installation

### Requirements

* Python 3.10+

### Install from PyPI

```sh
pip install ghga-arcticfreeze
```

To use the `FrozenDict` type within Pydantic models, install the optional `pydantic`
extra:

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

This package is a member of the [GHGA monorepo](https://github.com/ghga-de/ghga) and is
developed from the repository root rather than on its own. The repository ships a
devcontainer with the whole toolchain: open it in VS Code and run
`Remote-Containers: Reopen in Container`, or set the environment up directly with
`just sync`.

The usual tasks, run from the repository root (see
[ADR-0015](https://github.com/ghga-de/ghga/blob/main/docs/adr/0015-task-runner.md) for the
full recipe list):

```bash
just sync                         # install every member plus the shared dev toolchain
just test libs/ghga-arcticfreeze  # this member's test suite
just lint                         # ruff check + format check across the workspace
```

## License

This repository is free to use and modify according to the
[Apache 2.0 License](https://github.com/ghga-de/ghga/blob/main/libs/ghga-arcticfreeze/LICENSE).
