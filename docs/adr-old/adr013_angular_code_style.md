# Angular Code Style

Date: 2024-09-24

## Summary

In the context of **style rules and standards use in our new angular project**

facing **a need for homogenous code style and seamless onboarding and development**

we decided for **using the [Angular Style Guide](https://angular.dev/style-guide) and [linter plugins](https://www.npmjs.com/package/@angular-eslint/eslint-plugin) to enable it**

and neglected **to come up with our own set of rules and standards, making decisions on every option ourselves**

to achieve **a quick start of development and a seamless integration of standard tools (like 'ng generate ...')**

accepting that **this is not a highly individual solution**.

## Details

### Status

**accepted**

### Context & Requirements

Starting a new project requires coming up with naming conventions and structure. Angular provides tooling for this (ng generate) that has a built-in standard naming convention. Going with the default here has no real downside and removes the need to customize the schemas. There is a long list of theoretical decisions that do not really incur advantages or disadvantages - it is simply a choice that has to be made and stuck by.

Apart from the file structure conventions and naming conventions the guide proposes, the Angular Style Guide recommends using the [single responsibility principle](https://en.wikipedia.org/wiki/Single-responsibility_principle), which is a good indication.

Ultimately, naming style for variables, components, folders, services etc. (i.e. PascalCase vs. camelCase) and structuring a codebase is not massively influential on the project - but sticking to the guide *is*. To be able to navigate a codebase, it is useful to have clear structure and easy-to-follow patterns. The Angular Style Guide provides one such pattern that aligns with the tooling that Angular provides.

Since these styles are the de-facto standard for Angular projects, there is also some external tooling to enable those rules that can be checked automatically which would be more difficult to acchieve with self-defined standards.

An advantage of the guide is that it also offers reasoning for the rules, which helps to *understand* them instead of simple rote memorisation.

### Decision

Use the Angular Style Guide and enforce it by using '@angular-eslint/eslint-plugin' with the recommended rules enabled to enforce the rules that can be tested statically.

### Consequences

We can use default tooling (i.e. get started quicker) but will have to read the guide before we do. If we notice that there are issues with this guide, we can choose to make adaptations later but this guide has been used in very many projects and major issues are unlikely. Additionally, this removes personal preference from some review discussions because we can refer to the style guide (or the linter will do the work for us).

### Alternatives

We could write our own rules and define custom linter rules with a generic enough linting framework. We would also have to discuss every detail.
