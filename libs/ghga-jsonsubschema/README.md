# GHGA JSON Subschema

> **Note:** This is a fork of [IBM/jsonsubschema](https://github.com/ibm/jsonsubschema) maintained by the [German Human Genome-Phenome Archive (GHGA)](https://www.ghga.de/). It was created to bring in necessary fixes, updates, and functionality required by GHGA-related projects.

**ghga-jsonsubschema** checks if one JSON schema is a subschema (subtype) of another.

For any two JSON schemas s1 and s2, s1 <: s2 (reads s1 is subschema/subtype of s2) if every JSON document instance that validates against s1 also validates against s2.

jsonsubschema is very useful in analysing schema evolution and ensuring that newer schema versions are backward compatible.
jsonsubschema also enables static type checking on different components of a system that uses JSON schema to describe data interfaces among the system's different components.

The details of JSON subschema are covered in the [ISSTA 2021 paper](https://dl.acm.org/doi/10.1145/3460319.3464796) by Andrew Habib, Avraham Shinnar, Martin Hirzel, and Michael Pradel, the original authors of this library.

## I) Installation

### Requirements

* Python 3.13+

### A) Install from PyPI

```sh
pip install ghga-jsonsubschema
```

### B) Install from source

```sh
git clone https://github.com/ghga-de/ghga-jsonsubschema.git
cd ghga-jsonsubschema
uv sync
```

## II) Running subschema

JSON subschema provides two usage interfaces:

### A) CLI interface

1. Create two JSON schema examples by executing the following:

```sh
echo '{"type": ["null", "string"]}' > s1.json
echo '{"type": ["string", "null"], "not": {"enum": [""]}}' > s2.json
```

2. Invoke the CLI by executing:

```sh
python -m jsonsubschema s2.json s1.json
```

### B) Python API

```python
from jsonsubschema import is_subschema

def main():
    s1 = {'type': "integer"}
    s2 = {'type': ["integer", "string"]}

    print(f'LHS <: RHS {is_subschema(s1, s2)}')

if __name__ == "__main__":
    main()
```

## III) Development

Set up a local development environment:

```sh
uv sync --extra dev
uv run pre-commit install
```

Run the test suite:

```sh
uv run pytest tests/
```

Run the test suite with coverage:

```sh
uv run coverage run -m pytest tests/
uv run coverage report
```

## License

This repository is distributed under the terms of the Apache 2.0 License, see [LICENSE.txt](LICENSE.txt).
