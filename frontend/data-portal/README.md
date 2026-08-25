# GHGA Data Portal

This is the front-end application for the GHGA data portal. It lives in the [GHGA monorepo](../../README.md) as a self-contained pnpm workspace with its own lockfile, and is not part of the `uv` workspace that holds the services and libraries.

<!-- toc -->

- [Technology stack](#technology-stack)
- [Local development](#local-development)
  - [The four modes](#the-four-modes)
  - [Per-developer settings](#per-developer-settings)
  - [API requests & the backend](#api-requests--the-backend)
  - [Authentication](#authentication)
- [Code scaffolding](#code-scaffolding)
- [Building](#building)
- [Package Manager](#package-manager)
  - [Dependency overrides](#dependency-overrides)
- [Linter, Commits, and Documentation](#linter-commits-and-documentation)
  - [Ease of use](#ease-of-use)
- [Automated tests](#automated-tests)
  - [Test levels](#test-levels)
  - [Unit-tests](#unit-tests)
  - [End-to-End tests](#end-to-end-tests)
    - [Issues relating to headed execution](#issues-relating-to-headed-execution)
- [Analytics](#analytics)
- [The Architecture Matrix](#the-architecture-matrix)
- [AI assisted coding](#ai-assisted-coding)
- [References](#references)
- [License](#license)

<!-- tocstop -->

## Technology stack

This project is a single Angular application designed as a modularized frontend monolith. Major building blocks:

- Angular (version 22)
- Angular Material
- Tailwind CSS (version 4)
- Unit testing: Vitest
- E2E testing: Playwright
- API mocking in development: Mock Service Worker (MSW)

## Local development

To start a local development server, run this from the repository root:

```bash
just fe-dev
```

Once the server is running, open your browser and navigate to `http://localhost:8080/`. The application will automatically reload whenever you modify any of the source files.

By default, this will not use a proxy configuration; the API will be provided via the mock service worker, and the authentication will be faked as well.

The MSW handlers in `src/mocks` intentionally return static responses. We avoid adding complex backend logic to mocks to prevent duplicating server behaviors in the frontend codebase, which can differ or drift over time and produce misleading local test results.

The same mock layer also serves the Playwright tests, so this decision shapes what those tests are able to prove. See [Automated tests](#automated-tests) for the consequences.

### The four modes

The API and the authentication are two independent switches, giving four modes:

| Command                    | API                | Authentication     | Browse at                        |
| -------------------------- | ------------------ | ------------------ | -------------------------------- |
| `just fe-dev`              | MSW mocks          | faked              | `http://localhost:8080/`         |
| `just fe-dev-backend`      | proxied to backend | faked              | `http://localhost:8080/`         |
| `just fe-dev-oidc`         | MSW mocks          | real OIDC provider | `https://data.staging.ghga.dev/` |
| `just fe-dev-backend-oidc` | proxied to backend | real OIDC provider | `https://data.staging.ghga.dev/` |

Each recipe is a thin wrapper around `node run.js --dev` with `--with-backend` and `--with-oidc` in the corresponding combination, which you can also run directly from this directory. The `run.js` launcher is what generates `public/config.js` from the settings before handing over to `ng serve`, so a bare `pnpm start` is not equivalent — it serves the application without a fresh runtime configuration.

The settings themselves come from three places, each overriding the previous one: `data-portal.default.yaml` (the same defaults the production image uses), `data-portal.dev.yaml` (the development overrides, e.g. the `Development` ribbon and the `ghga-dev-client` OIDC client), and finally the environment, including [`local.env`](#per-developer-settings).

### Per-developer settings

Settings that differ per developer — above all the credentials that must not be committed — belong in `local.env` in this directory. Nothing creates it for you and the dev server runs fine without it; copy the template when you first need one:

```bash
cp local.env.example local.env
```

The copy is also how you pick up keys added to `local.env.example` later, so it is worth a glance at the template when a new setting appears.

Every key of `data-portal.default.yaml` can be set there as `data_portal_<key>`, and everything in the file also becomes a plain environment variable, so settings that no YAML key backs (such as `data_portal_ignore_cert`, which `proxy.conf.mjs` reads) work too. A typical file looks like this:

```env
data_portal_base_url=https://data.staging.ghga.dev
data_portal_basic_auth=USERNAME:PASSWORD
data_portal_oidc_client_id=THE_OIDC_CLIENT_ID
```

Variables already present in the environment win over the file, so `data_portal_base_url=... just fe-dev-backend` overrides it for a single run.

### API requests & the backend

If you want to test the application against the backend provided by the staging deployment, then run:

```bash
just fe-dev-backend
```

In this case, a proxy configuration will be used that proxies all API endpoints to the staging environment, while the application itself is still served by the development server. You can change the name of the staging backend via the setting `data_portal_base_url`; by default it will be `data.staging.ghga.dev`.

If the staging backend requires an additional Basic authentication, you can set it in `data_portal_basic_auth`.

### Authentication

If you want to test authentication using the real OIDC provider, then run:

```bash
just fe-dev-oidc
```

In this mode, the `data_portal_oidc_client_id` and the other OIDC settings must be set properly as required by the OIDC provider.

The provider redirects back to a registered URI that carries no port number, so this mode is not free to choose where it listens: the development server switches to HTTPS on port 443, under the hostname of the backend rather than `localhost`. Three things follow from that, and the `just` recipe takes care of the first two:

- **A certificate.** `just fe-cert` creates a local CA in `.certs/` and a certificate for the backend hostname signed by it (both gitignored). Add `.certs/ca-cert.pem` to the trusted certificates of your web browser or host computer to avoid the warnings when loading the page. Only the CA needs to be trusted, so re-issuing the certificate for a different hostname later does not mean touching the browser again.
- **Permission to bind port 443.** The dev container shares the host's network namespace, and therefore its rule that only root may bind ports below 1024. Instead of relaxing that on your machine, the recipe grants `cap_net_bind_service` to the container's `node` binary once, using `sudo`. A container rebuild discards it and the next run grants it again.
- **A hosts entry on your host computer**, mapping the backend hostname to `127.0.0.1`, so that the browser reaches the development server rather than the real deployment. With the default backend you then browse the application at `https://data.staging.ghga.dev`. (Inside the container, `run.js` adds the opposite entry — the hostname to the deployment's real address — so that the proxy still reaches the actual backend.)

To test against the real backend and with the real OIDC provider at the same time:

```bash
just fe-dev-backend-oidc
```

## Code scaffolding

The Angular CLI includes powerful code scaffolding tools. To generate a new component, run:

```bash
ng generate component component-name
```

or

```bash
ng g c component-name
```

for short.

For a complete list of available schematics (such as `components`, `directives`, or `pipes`), run:

```bash
ng generate --help
```

## Building

To build the project run:

```bash
ng build
```

This will compile the project and store the build artifacts in the `dist/` directory. By default, the production build optimizes the application for performance and speed.

Site verification files that shall be deployed at the root path in production can be specified in the `root_files` setting, using file names as properties and file contents as values.

## Package Manager

This project uses pnpm to install dependencies, which is a replacement for the much slower npm. Run

```bash
pnpm install
```

to install the dependencies, or `just fe-install` from the repository root to install them exactly as CI does (`--frozen-lockfile`).

You do not normally need either: the dev container provisions both stacks when it is created, installing these dependencies along with the Chromium build that Playwright uses ([`.devcontainer/post-create.sh`](../../.devcontainer/post-create.sh)). Only `pnpm e2e:all` needs the other browsers, which `pnpm exec playwright install firefox webkit` adds.

### Dependency overrides

There are currently **no dependency overrides** in use.

When a transitive dependency needs to be pinned (for example to pull a security patch that a direct dependency has not yet picked up), add a `.pnpmfile.cjs` file at the repository root with a `readPackage` hook, list the override here together with its reason and removal criteria, and run `pnpm install` to refresh `pnpm-lock.yaml`. Review such overrides from time to time and remove them once no longer necessary.

> Historical note: overrides for `picomatch`, `ajv`, and `uuid` were previously required because `@compodoc/compodoc@1.x` pulled vulnerable transitive versions. They were removed after upgrading to `@compodoc/compodoc@2`, which resolves those dependencies to patched versions natively.

---

**NOTE**

You should not have a `package-lock.json` but instead a `pnpm-lock.yaml`. You can still use npm for running other commands or to install global packages but not to add dependencies or to install all dependencies. Configuration of pnpm overrides should be done in `.pnpmfile.cjs` rather than in `package.json`.

---

## Linter, Commits, and Documentation

The repository is set up in such a way to only allow linted commits. That means commits are blocked if they cause linter errors (currently, warnings are accepted). This ensures that code quality standards are maintained without building up technical debt that has to be fixed later on.

Since the move into the monorepo the hooks come from the root `.pre-commit-config.yaml` rather than from Husky ([ADR-0018](../../docs/adr/0018-pre-commit-hooks.md)); ESLint and Prettier run over the files you touched, out of this package's own `node_modules`, so they are the same versions `pnpm lint` and `pnpm format:check` use. Install them once per clone with `just hooks` from the repo root — the dev container already does.

To ensure deterministic behavior, the pre-commit hook _does not_ attempt to fix linter errors. Most of the time, you will be fine by simply running `ng lint --fix`, which attempts to automatically fix most of the issues. If we ran that in the hook, however, you would be committing different code than the one you checked. So if you cannot commit your code, run lint fix. If that doesn't resolve all the issues (which you can see by running `ng lint`), resolve those issues and try again. Formatting is not auto-fixed either: run `pnpm format` (or `just fe-format`).

### Ease of use

For comfort, we are adding these shorthands: `pnpm lint`, `pnpm lf` (for `lint --fix`), and `pnpm run docs` (to build and serve the documentation; use `pnpm run docs` rather than `pnpm docs`, because pnpm has a built-in `docs` command that shadows the script). Apart from seeing the linter warnings when you (try to) commit or run the linter manually, your IDE should also show you these warnings in the code, and fixing (the auto-fixable ones) should be offered in the context menu on hover or via `Ctrl-.`.

> Note: when generating the docs, Compodoc prints a `Parse error: JSON5: invalid character '(' …` followed by `Routes parsing error, … trying to fix that later`. This is a harmless Compodoc limitation with Angular's arrow-function lazy routes (`loadComponent: () => import(...)` and functional `canActivate` guards) in `src/app/app-routes.ts`: Compodoc recovers on its own and the routes page is still generated. Nothing to fix on our side — it may go away with a future Compodoc release.

## Automated tests

### Test levels

Two levels of automated tests live in this repository, and a third lives elsewhere. They can prove quite different things, so it is worth choosing deliberately:

| Level                    | Runs against                                                                               | Answers                                           |
| ------------------------ | ------------------------------------------------------------------------------------------ | ------------------------------------------------- |
| Unit tests (Vitest)      | mocked services, mocked HTTP backend                                                       | does this service or component behave correctly?  |
| "E2E" tests (Playwright) | the real app in a real browser, with the API served by the [MSW mocks](#local-development) | is the application assembled and wired correctly? |
| GHGA archive test bed    | the real backend and database, in a separate repository                                    | does this flow actually work end to end?          |

Unit tests are the default and carry most of the coverage: request shapes, state transitions, cache invalidation, rendering and event wiring all belong there. The two other levels each add something the level above cannot see, and each costs more to run.

### Unit-tests

We are using [Vitest](https://vitest.dev/) for unit testing in this project. If possible, the queries and matchers from the [Testing Library](https://testing-library.com/) should be used. See the documentation for the [Angular Testing Library](https://testing-library.com/docs/angular-testing-library/intro/) and [jest-dom](https://testing-library.com/docs/ecosystem-jest-dom/). Note that jest-dom also supports Vitest, not just Jest.

The unit tests are not included in the linting process and can be executed separately. The following variants of running the tests are provided:

- `pnpm test` - run unit tests once
- `pnpm test:watch` - watch mode
- `pnpm test:ui` - interactive tests in the browser

Note: the VS Code Vitest extension runs plain `vitest` directly, which does not work for Angular component tests in this repository (external `templateUrl`/`styleUrl` and Angular TestBed setup are handled by the Angular test builder). Use `pnpm test` / `pnpm test:ui` instead. See also [this issue](https://github.com/angular/angular-cli/issues/31734).

### End-to-End tests

We are using [Playwright](https://playwright.dev/) for end-to-end (e2e) testing in this project. See the [documentation for Playwright](https://playwright.dev/docs/intro) for details.

"End-to-end" is admittedly a misnomer here. These tests do not reach the actual backend and database: the API is served by the same [MSW mocks](#local-development) that back the development server, and those return static responses by design. What is covered is the frontend from the browser inwards — everything above the network boundary. Comprehensive end-to-end tests for real backend behavior are maintained in the separate GHGA archive test bed repository.

Within that boundary, however, these tests are considerably more real than unit tests, and catch a class of problems unit tests structurally cannot:

- **The application really boots.** It starts from `app.config.ts` with the actual providers, routes lazy-load their real chunks, and guards run. Unit tests assemble a `TestBed` per spec and never exercise that configuration.
- **Requests are really issued.** They travel the whole `HttpClient` chain, including the caching and CSRF interceptors. Unit tests use `HttpTestingController`, which replaces the backend and only sees the interceptors a spec explicitly provides, so an interceptor misconfiguration is invisible there.
- **The real services run.** Unit tests replace services with hand-written mocks, which can silently drift from the API of the service they stand in for. Here the actual implementations are used, against each other.
- **It is a real browser.** Layout, focus handling, Angular Material overlays (dialogs, menus, snack bars) and view transitions all behave as they do for users, none of which jsdom reproduces. `pnpm e2e:all` additionally runs across the configured browsers.
- **Journeys span components and pages.** Navigation, shared services and cross-page state are exercised together rather than one unit at a time.
- **The expected API contract is checked.** Mock handlers are registered per URL and query parameters, so a request the application makes that no handler matches surfaces immediately.

What they cannot show is anything that depends on the backend actually changing state, because the mocks answer identically before and after a mutation. Do not write a test here that performs a change and then asserts that the change is reflected — it could only assert that a request was sent, which a unit test does more precisely and far more cheaply. Such flows belong in the archive test bed, which is more expensive to run.

Treat the tests in this repository as a fast smoke layer: keep them few and cheap, so they stay useful for quick feedback during frontend development.

They need only the development server — the API is mocked in the browser — so the demo platform (`just up` in the monorepo) is not required for them and only competes for memory. If a run hangs with no output at all, that competition is the first thing to check; `just down` frees it. `playwright.config.ts` prints a warning when memory is already low.

- `pnpm e2e` - run e2e-tests in headless mode on Chromium (fast local default)
- `pnpm e2e:all` - run e2e-tests in headless mode on all configured browsers using `--workers=2`
- `pnpm e2e:headed` - run e2e tests in headed mode
- `pnpm e2e:debug` - run e2e tests in headed mode with Playwright inspector
- `pnpm e2e:report` - open HTML report for e2e tests

Worker configuration:

- Default is `1` worker for stability.
- For faster local runs with the same command, do `export PLAYWRIGHT_WORKERS=<number of workers>`.
- If tests get flaky, lower the value (or return to `1`).

Stopping early:

- A local run stops at the first failure, which is usually what you want while fixing something.
- CI stops after 5, so that a single broken test can be reported for each of the three browsers rather than aborting the remaining tests after the first of them. Beyond that the suite is broken enough that stopping saves more than it hides.

Timeouts:

- The per-test timeout is raised to 60s and the `expect` timeout to 10s, well above the Playwright defaults. CI runners are far slower than a local machine: logging in and reaching an admin page alone costs around 15 seconds there, and even a mocked request can take more than a second, which used to exhaust the default 30s budget mid-test.
- These are upper bounds for tests that are genuinely stuck, not targets. A test that only passes because of them is telling you something — check the Playwright trace before raising them further.

Recommendations for writing stable e2e tests:

- Assert stable end states (final URL, final title, final visible content), not transient intermediate states.
- Use small bounded retries for known flaky UI transitions (menu/dialog open, click-triggered navigation).
- Keep retries minimal (usually 1-2 attempts) and always retain a strict final assertion.

Note: The Playwright HTML reporter is configured to **not auto-open** at the end of `pnpm e2e` runs, so test commands terminate cleanly in CI and local terminals.

Reports are still generated in `playwright-report/` and can be viewed on demand:

- Open the report file directly: `playwright-report/index.html`
- Or start the Playwright report server manually: `pnpm e2e:report`

Like for unit testing, you can also [use the VS Code extension for Playwright](https://playwright.dev/docs/getting-started-vscode) to run tests interactively using the test explorer in the side bar. VS Code is able to support different test providers (like Vitest and Playwright) along with each other.

#### Issues relating to headed execution

Headed execution (`pnpm e2e:headed`, `pnpm e2e:debug`, `pnpm e2e:ui`) needs an X11 server on the host, and a dev container that can reach it. The container does not mount one by default, because the path to mount differs per host operating system and a mount that fits one host makes container creation fail on another — see the comment above `mounts` in [`.devcontainer/devcontainer.json`](../../.devcontainer/devcontainer.json), which is where you add it for your own host, together with a matching `DISPLAY` in `containerEnv`. Rebuild the container afterwards.

On macOS, you can use [XQuartz](https://www.xquartz.org/). On Windows with WSL 2, you can use the built-in WSLg as X11 server. See [here](https://github.com/microsoft/wslg/wiki/Diagnosing-%22cannot-open-display%22-type-issues-with-WSLg) if that is not working properly.

The directory `/tmp/.X11-unix` should exist in the container and should be mounted on the corresponding host directory, which is `/mnt/wslg/.X11-unix` for WSLg. If you run `ls /tmp/.X11-unix`, it should show `X0`. You may also need to add `/tmp/.X11-unix` to the virtual file shares in Docker Desktop under Linux, and run `xhost +local:docker` on the host system.

Note that a headed run is rarely the shortest way to see what a failing test saw: the HTML report and the Playwright trace it embeds are available from a plain headless run, and neither needs a display.

## Analytics

This SPA uses Umami for event tracking. Every clickable item has a property `data-umami-event` that is globally unique and which should clearly identify both the action and the environment it is occurring in. Furthermore, there's a limit of 50 characters for these event names - otherwise they will be ignored by the backend.

## The Architecture Matrix

This application is built as a modularized frontend monolith (a "modulith") using vertical slices and layers as module boundaries, which are enforced using the linter.

The vertical slices correspond to the different feature areas or bounded contexts within the application, such as _metadata_ or _access-requests_. Additionally, we have a vertical slice called _portal_ that contains all overarching features, such as the home page (which displays a metadata summary) and the user profile page (which shows the user's access requests). Another slice, called _shared_, provides UI components or utilities used across all feature areas. Authentication and user session handling are implemented in a separate slice called _auth_.

The horizontal layers are named _features_ (for feature components, i.e., smart components), _ui_ (for presentational components, i.e., dumb components), _services_ (for accessing domain objects and corresponding application logic), _models_ (for interfaces of domain objects), and _utils_ (for feature-specific utility functions). The _services_ layer primarily contains Angular services, while the _utils_ layer includes pure pipes, guards, and custom utility functions.

This results in the following architecture matrix:

| portal   | metadata | access-requests | ... | auth     | shared   |
| -------- | -------- | --------------- | --- | -------- | -------- |
| features | features | features        | ... | features | features |
| ui       | ui       | ui              | ... | ui       | ui       |
| services | services | services        | ... | services | services |
| models   | models   | models          | ... | models   | models   |
| utils    | utils    | utils           | ... | utils    | utils    |

To create a clean architecture, the following rules are checked when importing modules from the architecture matrix:

- Modules within a vertical slice must only import modules from the same slice, as these slices represent bounded contexts.
- An exception is that all vertical slices are allowed to use modules from the _shared_ vertical slice.
- Another exception is that the _portal_ slice is allowed to use feature components from other feature areas.
- Additionally, the three bottom layers of the _auth_ slice may be used in other slices.
- Each module is only allowed to use modules from the layers below it.
- An exception is that the _ui_ layer may not use modules from the _services_ layer.

## AI assisted coding

This project is best supported in VS Code with GitHub Copilot, but tools like Claude Code can also be used.

- `AGENTS.md` is the entrypoint for AI-specific instructions; agents should also follow this `README` and relevant guidance in `docs/`.
- If you use the Angular CLI MCP server integration (for example via Copilot Chat tools), it can help with Angular-specific guidance and code generation.
- After updating Angular dependencies, it can be useful to run `MCP: Reset Cached Tools` once so the MCP tool metadata is refreshed for the new Angular/CLI version.
- Keep `AGENTS.md` up to date when you change major tooling (Angular, Angular Material, Tailwind, testing/build scripts), so AI-assisted changes stay consistent with project conventions.

## References

- [Playwright](https://playwright.dev/) and [the docs for it](https://playwright.dev/docs/intro).
- [Angular CLI Overview and Command Reference](https://angular.dev/tools/cli).
- [Pnpm](https://pnpm.io/) and [the docs for it](https://pnpm.io/motivation).
- [Vitest](https://vitest.dev/) for unit tests. [Testing Library](https://testing-library.com/) for queries with an [Angular integration](https://testing-library.com/docs/angular-testing-library/intro/) and [jest-dom](https://testing-library.com/docs/ecosystem-jest-dom/).

## License

This project is licensed under the Apache License, Version 2.0. See the [LICENSE](LICENSE) file for more details.
