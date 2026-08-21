# Documentation: jsonsubschema

## 1. Introduction

**jsonsubschema** is an open-source Python library designed to identify **data compatibility bugs** by analyzing JSON schemas. Unlike standard validators that check if a specific JSON document matches a schema, `jsonsubschema` performs a static analysis of the relationship between two schemas themselves.

This allows developers to detect potential issues—such as breaking API changes or incompatible data pipeline steps—before any actual data is processed.

## 2. The Core Concept: Subschema Checking

A schema $s$ is considered a **subschema** (or subtype) of another schema $t$ (denoted as $s <: t$) if and only if **every JSON document** that is valid according to $s$ is also guaranteed to be valid according to $t$.

The tool provides three possible outputs for a check:

* **True:** $s$ is definitely a subschema of $t$.
* **False:** $s$ is definitely not a subschema of $t$.
* **Unknown:** The check involves unsupported complex features (e.g., recursive references), and a definitive answer cannot be provided.

## 3. The 3-Step Processing Pipeline

JSON Schema is highly flexible; two schemas can look completely different but describe the exact same set of documents. To handle this, `jsonsubschema` uses a three-stage pipeline:

### Step 1: Canonicalization

This stage transforms schemas into a standardized, "canonical" form to reduce syntactic variety.

* **Type Splitting:** Mixed types (e.g., `type: ["string", "null"]`) are split into explicit logical disjunctions using `anyOf`.
* **Explicating Defaults:** Omitted default values are added explicitly to ensure no ambiguity.
* **Standardizing Types:** For instance, `boolean` types are converted into an `enum` of `[true, false]`, and `integer` is represented as a `number` with a `multipleOf: 1` constraint.
* **String Uniformity:** Constraints like `minLength` and `maxLength` are converted into equivalent regular expression patterns.

### Step 2: Simplification

The simplifier further reduces complexity by eliminating redundant logical constructs.

* **Enum Elimination:** Non-boolean enumerations are replaced by type-specific restrictions (e.g., an enum of strings becomes a regular expression).
* **Logical Reduction:** The tool attempts to eliminate `not`, `allOf`, `anyOf`, and `oneOf` keywords where possible, aiming for a structure similar to a "disjunctive normal form".

### Step 3: Subtype Checking

The final step extracts **type-homogeneous fragments** (parts of the schema describing a single JSON type) and compares them using dedicated type-specific checkers.

* **Numbers:** Uses a complex `_is_number_subtype` relation to compare ranges and `multipleOf` constraints, even across negated schemas.
* **Objects:** Checks if the required properties of the super-schema are present in the subschema and ensures that `patternProperties` constraints are compatible.
* **Arrays:** Verifies size bounds and ensures that the schema for items at each index in the subschema is a subtype of the corresponding item schema in the super-schema.

## 4. Developer Use Cases

The tool is particularly effective for:

* **API Evolution & Backward Compatibility:** In versioned APIs (e.g., using semantic versioning), you can verify that a new schema version is a super-schema of the old one. If not, you have a **breaking change** that requires a major version bump.
* **Machine Learning (ML) Pipelines:** Static type-checking for ML operators. You can verify if the output schema of one operator is a subschema of the input schema required by the next operator, preventing crashes after hours of computation.

## 5. Performance and Reliability

* **Precision:** In real-world tests, the tool achieved **100% precision and correctness**, meaning it never gives a false positive "True" or "False".
* **Recall:** It successfully decides the subschema question for approximately **93.5%** of real-world schema pairs.
* **Efficiency:** For moderately sized schemas, checks typically terminate within a few seconds, with performance scaling **linearly** relative to schema size.

## 6. Limitations and "Unknown" Results

The tool currently returns `unknown` for a small subset of features (approx. 6.5% of cases in the wild):

* **Recursive References:** Schemas using `$ref` to refer to themselves.
* **Complex Negations:** Certain combinations of `not` and `anyOf` for structured types (objects and arrays).
* **Non-regular Regex:** While standard regex is supported for string patterns, non-regular patterns may cause issues.

## 7. Resources

* **Research Paper:** "Finding Data Compatibility Bugs with JSON Subschema Checking" (ISSTA '21) - [ACM Digital Library](https://dl.acm.org/doi/10.1145/3460319.3464796)
