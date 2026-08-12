# Create baseline for Angular implementation (Hippopotamus)

**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).

## Scope

### Outline:

The goal of this epic is to create a repository that can be used as a baseline for the re-implementation of the GHGA Data Portal in Angular.

The baseline application should follow the decisions that we made in the [Bottlenose Dolphin](../59-bottlenose-dolphin/technical_specification.md) epic.

It should already implement the proper overall visual layout and design (styling and theming). It should be runnable against the mock backend and the real backend and should exemplify using at least one REST endpoint (e.g. the global stats shown on the homepage). It should cover all tooling to provide a good developer experience, linting and running unit and e2e testes.

### Included/Required:

- Create a new GitHub repository "data-portal" from scratch that will eventually supersede the existing "data-portal-ui" repository.
- The experimental repository "angular-portal" will only be used as a reference and then archived.
- Use a suitable Node.js based docker image for the devcontainer.
- Create the base Angular project files and directory structure using `ng new` with Angular v19.
- Configure the application to run zoneless and without SSR according to [ADR017](https://github.com/ghga-de/adrs/blob/main/docs/adrs/adr017_server-side_rendering_in_angular.md).
- Configure the project to use pnpm as a package manager as specified in [ADR015](https://github.com/ghga-de/adrs/blob/main/docs/adrs/adr015_node_runtime_selection.md).
- Add pre-commit hooks and configuration for Prettier, ESLint and other useful linters.
- Add `@angular-eslint/eslint-plugin` with the recommended rules as specified in [ADR013](https://github.com/ghga-de/adrs/blob/main/docs/adrs/adr013_angular_code_style.md).
- Add subdirectories as specified in [ADR018](https://github.com/ghga-de/adrs/blob/main/docs/adrs/adr018_frontend_architecture.md).
- Add `eslint-plugin-boundaries` configuration as specified in [ADR018](https://github.com/ghga-de/adrs/blob/main/docs/adrs/adr018_frontend_architecture.md).
- Add and configure ESLint plugin to enforce documentation via JSDoc as specified in [ADR014](https://github.com/ghga-de/adrs/blob/main/docs/adrs/adr014_angular_project_documentation.md).
- Add support for Compodoc as specified in [ADR014](https://github.com/ghga-de/adrs/blob/main/docs/adrs/).
- Add the latest Angular Material version as a dependency as specified in [ADR019](https://github.com/ghga-de/adrs/blob/main/docs/adrs/adr019_responsive_design_systems.md) and [ADR020](https://github.com/ghga-de/adrs/blob/main/docs/adrs/adr020_angular_component_library.md).
- Add Tailwind CSS as a dependency as specified in [ADR022](adr022_db_migrations.md).
- Add a Node.js run script that injects the runtime configuration and a configuration service that can be used by components and other services to fetch the configuration.
- Create the base components (app component, header, footer, landing page) and style them according to our existing corporate design, make everything look similar to the legacy application.
- Make sure the application uses the proper semantic tags according to [ADR016](https://github.com/ghga-de/adrs/blob/main/docs/adrs/adr016_semantic_web_technologies.md).
- Add a minimal multi-stage production docker file that uses the run script to inject the configuration without rebuilding the application and SWS (`static-web-server`) to serve it as a single-page application.
- Add and configure `cashew` for caching HTTP requests as a dependency.
- Add and configure `MSW` (Mock Service Worker) for mocking the backend as a dependency.
- Add authentication (login via LS Login, registration, 2FA) using `oidc-client-ts` (will be moved to the backend later). The profile page can be incomplete.
- Components that require authentication should be guarded and lazy-loaded.
- Provide and document a way to easily switch between testing the application manually on localhost against MSW and against the staging or testing backend deployment.
- Remove Karma and Jasmine and add Jest as well as `jest-preset-angular` and `jest-marbles` as dependencies for unit testing. 
- Add some example unit tests using Jest.
- Add and configure Playwright for e2e-testing. These tests only need to work with MSW. Later we may also add e2e-tests against the testing deployment in this repo, but they could also be added to the Archive Test Bed instead.
- Add some example tests with Playwright.

### Optional:

- Add one or two more feature components as examples.
- Add some useful shared utility functions or pipes.

### Not included:

- Implementation of all the feature components to reach feature-parity with the legacy application. This will be done in a follow-up epic.

## Human Resource/Time Estimation:

Number of sprints required: 2

Number of developers required: 3
