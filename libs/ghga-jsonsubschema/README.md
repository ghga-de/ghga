# GHGA JSON Subschema

> **Note:** This is a fork of [IBM/jsonsubschema](https://github.com/ibm/jsonsubschema) maintained by the [German Human Genome-Phenome Archive (GHGA)](https://www.ghga.de/). It was created to bring in necessary fixes, updates, and functionality required by GHGA-related projects.

**ghga-jsonsubschema** checks if one JSON schema is a subschema (subtype) of another.

For any two JSON schemas s1 and s2, s1 <: s2 (reads s1 is subschema/subtype of s2) if every JSON document instance that validates against s1 also validates against s2.

jsonsubschema is very useful in analysing schema evolution and ensuring that newer schema versions are backward compatible.
jsonsubschema also enables static type checking on different components of a system that uses JSON schema to describe data interfaces among the system's different components.

The details of JSON subschema are covered in the [ISSTA 2021 paper](https://dl.acm.org/doi/10.1145/3460319.3464796) by Andrew Habib, Avraham Shinnar, Martin Hirzel, and Michael Pradel, the original authors of this library.

## I) Obtaining the tool

### Requirements

* Python 3.8
* Other Python dependencies will be installed during the below setup process

You can either install subschema from the source code from GitHub or the PyPI package.

### A) Install from GitHub source code

Execute the following:

```sh
git clone https://github.com/ghga-de/ghga-jsonsubschema.git 
cd jsonsubschema
python setup.py install
cd ..
```

### B) Install from PyPI

Execute the following:

```sh
pip install jsonsubschema
```

## II) Running  subschema

JSON subschema provides two usage interfaces:

### A) CLI interface

1. Create two JSON schema examples by executing the following:

```sh
echo '{"type": ["null", "string"]}' > s1.json
echo '{"type": ["string", "null"], "not": {"enum": [""]}}' > s2.json
```

1. Invoke the CLI by executing:

```sh
python -m jsonsubschema.cli s2.json s1.json
```

### B) Python API

```sh
from jsonsubschema import isSubschema

def main():
    s1 = {'type': "integer"}
    s2 = {'type': ["integer", "string"]}

    print(f'LHS <: RHS {isSubschema(s1, s2)}')

if __name__ == "__main__":
    main()
```

## License

jsonsubschema is distributed under the terms of the Apache 2.0 License, see [LICENSE.txt](LICENSE.txt).

## Contributions

json-subschema is still at an early phase of development and we welcome contributions.
