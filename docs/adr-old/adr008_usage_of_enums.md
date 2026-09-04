# Naming and Usage of Enums

Date: 2024-03-08

## Summary

In the context of **enumerated values that are shared between components like backend, frontend, and database via JSON**

facing **the problem that there are multiple, incompatible enumeration types and naming conventions**

we decided for **using a naming convention that prefers PascalCase as shown in the examples below**

and neglected **alternative naming conventions that prefer SCREAMING_SNAKE_CASE**

to achieve **a naming convention that is easy on the eyes, appropriate for the used languages and makes conversion as simple as possible**

accepting that **there is a case mismatch beween Python enum names and values, and it does not go so well with GraphQL**.

## Details

### Status

**accepted**

### Context & Requirements

Both Python and TypeScript support different kinds of enums, e.g. numeric or string based, and both also support string literals as an alternative. To standardize the usage of enums in the codebase and to avoid problems when sharing enums between backend, frontend, and database, particularly due to conversion from and to JSON, we needed a common naming and usage convention for enums.

### Decision

We suggest the following conventions:

#### Python

The class name should be singular (except for bit fields) and not have the suffix `Enum`.

The names in an enum should be in `SCREAMING_SNAKE_CASE`, since this is a Python convention. The values should be the corresponding names in `PascalCase`, since this is less ugly. Do not use `auto()`.

The class should inherit from `StrEnum` (or from both `str` and `Enum` in older Python versions). This makes the enum JSON-serializable with the default encoder, resulting in the less ugly `PascalCase` string values.

Example:

```python
class VisaType(StrEnum):
    """The type of a visa"""

    AFFILIATION_AND_ROLE = "AffiliationAndRole"
    ACCEPTED_TERMS_AND_POLICIES = "AcceptedTermsAndPolicies"
    RESEARCHER_STATUS = "ResearcherStatus"
    CONTROLLED_ACCESS_GRANTS = "ControlledAccessGrants"
    LINKED_IDENTITIES = "LinkedIdentities"
```

#### TypeScript

The type name should follow the same convention as the Python class name.

The names in an enum should be in `PascalCase`, since this is a TypeScript convention. The values should be the same, so that de-serialization from JSON works with the default decoder. However, instead of a string enum with values that are the same as the names, we can simply use a unioned string literal type. This also has the advantage to not generate additional JavaScript code.

Example:

```ts
type VisaType =
  'AffiliationAndRole' |
  'AcceptedTermsAndPolicies' |
  'ResearcherStatus' |
  'ControlledAccessGrants' |
  'LinkedIdentities';
```

#### JSON, OpenAPI and Database

The enumerated values should be `PascalCase` strings.

### Consequences

Conversion from and to JSON works seamlessly following these conventions. Support for GraphQL may be more difficult because it uses upper case enum values.

### Alternatives

We could use `SCREAMING_SNAKE_CASE` everywhere. However, such strings look a bit ugly, and this is not the typical convention for TypeScript enum names. TypeScript string enums with `PascalCase` names and `SCREAMING_SNAKE_CASE` values could solve the latter problem and would be better suited when using GraphQL.

In cases where enum values are only used internally and not shared between components or stored in the database, enums with numeric values may also be appropriate.

## Links

- [Python support for enumerations](https://docs.python.org/3/library/enum.html)
- [TypeScript Enums](https://www.typescriptlang.org/docs/handbook/enums.html)
- [Enums vs String Literal Types in TypeScript ](https://brockherion.dev/blog/posts/enums-vs-typed-strings-in-typescript/)
- [TypeScript's Literal Types Are Better Than Enums](https://danielbarta.com/typescript-literal-types-are-stronger-than-enums/)
- [Enums vs. String Literal Unions in TypeScript](https://contra.com/p/W3ol7m3o-enums-vs-string-literal-unions-in-type-script)
