# Frontend architecture and modularization

Date: 2024-10-01

## Summary

In the context of **defining the overall architecture of our frontend application**

facing **the lack of a well-defined, maintainable, scalable, clean architecture like we have in the backend**

we decided for **building a light-weight "modulith" using vertical slices and layers as outlined below**

and neglected **the idea of dividing the application into micro frontends or using additional tooling like Nx**

to achieve **a simple, yet well-structured architecture that also can be enforced with linters**

accepting that **we will not have the need to embed applications built with different frameworks or by a different team**.

## Details

### Status

**accepted**

### Context & Requirements

On the backend side, we are using micro services with a "triple-hexagonal architecture," which enables us to achieve high code quality with well-structured, highly testable, and decoupled code.

On the frontend side, our existing React based application did not have an explicitly defined and enforced architecture, so that over time the structure became less consistent, and thereby harder to maintain and extend. Also, features like lazy-loading parts of the application were not implemented and would be difficult when the code is not decoupled well enough. We take the [decision to move from React to Angular](./adr002_angular_as_frontend_framework.md) as an opportunity to establish a well-defined and clean architecture on the frontend side as well.

Since we are already using micro services on the backend side to achieve the well-known benefits from this approach, another obvious question was whether we should also use micro frontends, which would give us similar benefits on the frontend side. Tools like [Nx](https://nx.dev) and concepts like module federation make building micro frontends nowadays a lot easier and more popular.

### Decision

We decided to build a lightweight, modularized frontend monolith (a "modulith") instead of going for a full-fledged micro frontend based approach.

The main argument for building micro frontends is that these can be implemented independently by different teams and using different frameworks. However, our frontend is developed by a single team, so this argument does not apply to us. Also, using different frameworks has many drawbacks. Even on the backend side, where it would be less problematic, we are using only one framework. The added complexity of micro frontends would outweigh their small benefits in our case.

Consequently, we also decided against using tools like [Nx](https://nx.dev/), which are designed to manage monorepos for large-scale and micro frontend solutions. For our modulith approach, such tools offer minimal benefits and instead introduce unnecessary complexity. Additionally, they complicate the process of upgrading our dependencies.

We decided to use a modularization that is roughly based on the architecture matrix suggested by Manfred Steyer in the article [Modern Architectures with Angular – Part 1: Strategic Design with Sheriff and Standalone Components](https://www.angulararchitects.io/blog/modern-architectures-with-angular-part-1-strategic-design-with-sheriff-and-standalone-components/).

Some implementation details regarding the architecture matrix have been added at the end of this ADR.

### Consequences

The architecture will make it a lot easier to maintain a clean project structure in the long run. This clean and consistent structure will also help when onboarding new developers. Even when adding new features, the feature areas will stay decoupled and can be maintained independently, without fearing to break other parts of the application or creating huge bundle sizes due to intermingled code.

A downside of this approach is that this architecture requires more discipline, forethought, and consideration when dividing the application into vertical slices. Another downside is that enforcing the architecture requires additional tooling and configuration, which must be maintained.

### Alternatives

One alternative would be to continue building the application with a less rigid structure, relying solely on the structure and code style guidelines provided by the Angular framework. However, we believe that we should go one step further to achieve a cleaner and scalable architecture following principles from domain driven design.

Another alternative would be to implement feature areas as sub-applications using the micro frontend pattern. We could also add more tooling like Nx that helps with building larger, composed applications. This would be more scalable when adding new sub-applications and development teams. Additionally, it could reduced build times when the application becomes more complex and new feature areas are added. However, we do not expect the complexity of our frontend to grow to a size where any of this would cause us problems.

### Additional Implementation Details

#### Definition of the Architecture Matrix

The vertical slices should correspond to the different feature areas or bounded contexts within the application, such as *metadata* or *access-requests*. Additionally, we should have a vertical slice called *portal* that contains all overarching features, such as the home page (which displays a metadata summary) and the user profile page (which shows the user's access requests). Another slice, called *shared*, should provide UI components or utilities used across all feature areas. Authentication and user session handling should be implemented in a separate slice called *auth*.

The horizontal layers should be named *features* (for feature components, i.e., smart components), *ui* (for presentational components, i.e., dumb components), *services* (for services accessing domain objects and corresponding application logic), *core* (for feature-specific business logic or domain objects), *pipes* (for simple, presentational logic implemented as pipes), *models* (for interfaces or schemas of domain objects), and *utils* (for simple feature-specific utility functions).

The resulting architecture matrix would look something like this:

| portal   | metadata | access-requests | ... | auth     | shared   |
|----------|----------|---------------- |-----|----------|----------|
| features | features | features        | ... | features | features |
| ui       | ui       | ui              | ... | ui       | ui       |
| services | services | services        | ... | services | services |
| core     | core     | core            | ... | core     | core     |
| pipes    | pipes    | pipes           | ... | pipes    | pipes    |
| models   | models   | models          | ... | models   | models   |
| utils    | utils    | utils           | ... | utils    | utils    |

To create a clean architecture, certain rules should be followed when importing modules inside the architecture matrix:

- Modules within a vertical slice should only import modules from the same slice, as these slices represent bounded contexts.
- An exception is that all vertical slices are allowed to use modules from the *shared* vertical slice.
- Another exception is that the *portal* slice is allowed to use feature components from other feature areas.
- Additionally, the non-component layers of the *auth* slice may be used in other slices.
- Each module is only allowed to use modules from the layers below it.
- An exception is that the *ui* layer may not use modules from the *services* and *core* layers.
- The *core* layer may not be necessary if all business logic is implemented in other layers already.

These rules already help avoiding cyclic dependencies, but care must still be taken to not create cyclic dependencies inside the above boundaries or by adding more exception rules. If there are cyclic dependencies in the injected services, Angular will show a runtime error, but some cyclic dependencies are less obvious. Sometimes the `forwardRef` function can be used to resolve these.

#### Tooling to Enforce the Architecture

The article mentioned above suggests using [Sheriff](https://github.com/softarc-consulting/sheriff) to enforce these rules. However, Sheriff is currently based on `index.ts` files ("barrels") to define its module boundaries. This approach can create problems with lazy-loading and tree-shaking when [using standalone components](./adr012_use_of_ngmodules.md). Additionally, Sheriff can only define rules based on either of the two dimensions of the matrix, not on the combination, and always checks all rules without allowing exceptions. Due to these limitations, using Sheriff is currently not feasible for us.

For the time being, we decided to use [eslint-plugin-boundaries](https://github.com/javierbrea/eslint-plugin-boundaries) instead of Sheriff. Although it is more complicated to configure and requires additional packages to support TypeScript, it provides more flexibility. It allows defining boundaries solely in the configuration without needing to create `index.ts` files. It also supports rule-specific error messages, which can be helpful for developers. At the time of writing, support for the current ESLint version is only available in a beta release of this plugin, with correspondingly limited documentation. Since this is only a developer tool, this is acceptable. We have already created a proof of concept solution that verified the beta version works and is flexible enough to enforce the rules listed above.

We also checked that our solution works well with [lazy-loading](https://angular.dev/guide/ngmodules/lazy-loading) and [tree-shaking](https://webpack.js.org/guides/tree-shaking/). In our example, the lazy-loaded bundle for the home page component would only contain the home page and metadata-summary components and code from lower layers that it depends on, but no other modules from the metadata feature area.

After the release of Sheriff v1 which is expected to support barrel-less modules, we can reconsider using Sheriff. It appears less complicated and has been specifically created for Angular applications using such an architecture matrix.

Note that Sheriff also provides an ESLint plugin, so both solutions are compatible with our [decision to use ESLint as a linting tool](./adr013_angular_code_style.md).

#### Possible directory structure

Here is an example directory structure of an Angular application implementing the above architecture matrix:

```
+---node_modules
+---public
+---src
    +---app
        +---access-requests
        ¦   +---features
        ¦   ¦   +---access-request-browser
        ¦   ¦   +---access-request-form
        ¦   ¦   +---user-access-requests
        ¦   +---models
        ¦   +---services
        ¦   +---ui
        ¦   ¦   +---access-request-detail
        ¦   ¦   +---access-request-list
        ¦   +---utils
        +---auth
        ¦   +---features
        ¦   +---models
        ¦   +---services
        ¦   +---ui
        ¦   +---utils
        +---metadata
        ¦   +---features
        ¦   ¦   +---metadata-browser
        ¦   ¦   +---metadata-details
        ¦   ¦   +---metadata-summary
        ¦   +---models
        ¦   +---services
        ¦   +---ui
        ¦   +---utils
        +---portal
        ¦   +---features
        ¦   ¦   +---footer
        ¦   ¦   +---header
        ¦   ¦   +---home
        ¦   ¦   +---profile
        ¦   +---services
        ¦   +---ui
        ¦   +---utils
        +---shared
            +---ui
            ¦   +---dummy
            +---utils
```
