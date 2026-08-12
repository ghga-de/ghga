# Angular implementation plan and migration strategy (Bottlenose Dolphin)

**Epic Type:** Exploratory Epic

## Principle Components of Exploration:

As outlined in [ADR002](https://github.com/ghga-de/adrs/blob/main/docs/adrs/adr002_angular_as_frontend_framework.md), we decided to migrate our existing GHGA data portal from React to Angular.

This exploratory epic is concerned with laying out a plan for achieving this goal that includes the most important architecture and design decisions that should be made upfront. We expect that these may be revised later, but we want to start with a solid and reasonable foundation to achieve a maintainable solution with our limited resources.

The following questions need to be investigated and answered in this context:

- Architecture and modularization:
  - Can or should we [vertically slice](https://www.youtube.com/watch?v=cVVMbuKmNes) the application?
  - Should we use the [micro frontend pattern and module federation](https://www.youtube.com/watch?v=8peHqzO7oqE)?
  - Do we want to integrate future frontend applications like for GHGA SPE and Atlas as some kind of sub-applications under a single host application as container, or do we want to develop them as independent applications?
  - Would [Nx](https://nx.dev/getting-started/why-nx) be useful for us? Should we use it to create a [monorepo](https://monorepo.tools/) for all UI related code?
  - Should we use [standalone components](https://v17.angular.io/guide/standalone-components)? Should we still use [NgModules](https://angular.dev/guide/ngmodules)?
  - If we do not use sub-applications, then we should still [lazy-load](https://angular.dev/guide/ngmodules/lazy-loading) modules that can only be used by authenticated users or data stewards. How can we do that?

- Code style and documentation:
  - Which code style do we want to use? Do we want to strictly follow the [Angular coding style guide](https://angular.dev/style-guide)?
  - How can we enforce the code style and other best practices regarding code quality (linting, using pre-commit)?
  - Are there linter rules for the Angular coding style guide?
  - How should the directory structure of the repository look like?
  - How and to what extend do we document the new codebase?
  - Are there any standards or tools that we should use for the documentation (JSDoc, Storybook)?
  - How do we enforce that e.g. all classes and methods are annotated with some minimal documentation?
  - Can we use some kind of automated documentation?
  - Shall we provide some high-level documentation that can be used to onboard new developers?

- Authentication:
  - How can [OIDC](https://openid.net/developers/how-connect-works/), [2FA](https://auth0.com/learn/two-factor-authentication), and user state management be integrated?
  - Should we use a client-side library [angular-auth-oidc-client](https://github.com/damienbod/angular-auth-oidc-client) or [oidc-client-ts](https://github.com/authts/oidc-client-ts) or [angular-oauth2-oidc](https://github.com/manfredsteyer/angular-oauth2-oidc)?
  - Should we instead move the OIDC client completely to the backend (auth adapter) for improved security, as [recommended by Philippe De Ryck](https://www.youtube.com/live/mORR3hpMaJQ)?

- Design system:
  - Which [design system](https://www.figma.com/blog/design-systems-101-what-is-a-design-system/) (e.g. Bootstrap, Material, Ant, Tailwind, Clarity, Carbon, Fluent, Chakra, Foundation) do we want to use? See our earlier evaluation [here](https://github.com/ghga-de/adrs/pull/5/).
  - While [Angular Material](https://material.angular.io/) looks like a natural choice, is it suitable for a mostly non-mobile application like ours with high information density? Particularly, do we need data grids (tables) and how well are they supported?
  - Settle on a component library. See our earlier evaluation [here](https://github.com/ghga-de/adrs/pull/9). Did we miss anything, is there anything new?
  - How important are responsive design and accessibility to us? How well is this supported by the chosen system/library?
  - Do we want to use plain CSS or SASS or SCSS syntax?
  - Do we want to design pages upfront, creating mockups or wireframes? If yes, which tools for the UI/UX design do we want to use?

- State management and other tooling:
  - Shall we use a dedicated state management solution (like NgRx, Akita, Elf or NgxZustand)? Or start with a [NGRX signal store](https://ngrx.io/guide/signals/signal-store) or simple custom services to manage state?
  - Should we primarily use [RxJS](https://rxjs.dev/) or [Signals](https://angular.dev/guide/signals)?
  - Should we build the app with our without [ZoneJs](https://angular.dev/guide/experimental/zoneless)?
  - Shall we make use of a caching library for HTTP requests like [NgHttpCaching](https://github.com/nigrosimone/ng-http-caching) or [cashew](https://github.com/ngneat/cashew)?
  - Are there any client libraries or development tools that we should make use of?

- Deployment and configuration:
  - How can we pass a runtime configuration similarly as we do with our microservices?
  - How can we inject the configuration into the application without rebuilding the complete application, as we currently do for the React app?
  - How can we rewrite the build and run steps from Python to JavaScript so that we do not need to install Python in the Docker container anymore?
  - What is the best way to serve the SPA in production? We currently use the [serve](https://www.npmjs.com/package/serve) package from npm in the React app. Is that still up to date and recommended?
  - How can we build a very slim Docker image for production that does not contain any build or development tools and other unnecessary components?
  - Which JavaScript runtime shall we use (Node with yarn or npm, Deno, Bun)?

- Searchability and performance:
  - Define a suitable HTML structure using semantic HTML.
  - Shall we support other semantic web technologies like schema.org with JSON-LD?
  - Can we make use of [deferrable views](https://angular.dev/guide/defer)?
  - Is it worthwhile for us to support server-side rendering (e.g. for SEO or faster loading)?
  - What is the current state of server-side-rendering in Angular? How much effort is it to make use of it?
  - How important is site performance (the "core web vitals") for us generally? Should we use tools like Lighthouse CI for measuring and testing it?

- Testing:
  - How can we (manually) test against the real backend? What would be a replacement for `setupProxy.js`?
  - How can we (manually) test against a mock backend? Shall we continue to use [MSW](https://mswjs.io/) with simple, ideally static responses?
  - What should be tested, and with which type of test? Would it be sufficient to have one kind of test?
  - Do we want to implement both unit/component tests and end-2-end-tests and in which proportions? Which degree of coverage do we want to achieve?
  - Which unit testing tool and test runner should we use?
  - Which end-to-end-testing tool (e.g. Cypress, Nightwatch, WebdriverIO, Puppeteer, Playwright)?
  - Do these tools work well with MSW? Can we run them as GitHub actions?

- Migration:
  - How many developer resources should we put into the re-writing? How quickly do we want to finish this?
  - How do we deal with new feature request before the migration is finished?
  - Which features should be implemented first?

For every major decision, an ADR should be created as part of this exploration.
Some questions can also be answered with a small proof-of-concept implementation.

Since reverting some decisions can be very costly, we should identify these and focus on them during this epic. We can spend less time on decisions that can be easily changed later.

For easily reversible decisions, we can choose any option that is good enough to get started. If it proves unfeasible during implementation or if better solutions arise, we can easily make changes.

## Not part of this Exploration:

All aspects that shall be ignored during the exploration:

- coding and implementation other than for demonstration and experimental purposes
- the specification of the exact components and services that will be used

## Material and Resources:

Here are some of the resources that should be consulted:

Angular:
- [Angular documentation](https://angular.dev)
- [Angular Signals: Complete Guide](https://blog.angular-university.io/angular-signals/)
- [Angular without ZoneJS (Zoneless)](https://angular.dev/guide/experimental/zoneless)

Micro frontends and monorepos:
- [Intro to Nx](https://nx.dev/getting-started/intro)
- [Restructuring to a Vertical Slice Architecture](https://www.youtube.com/watch?v=cVVMbuKmNes) (webinar, 2021)
- [Micro-Frontends with Module Federation: Beyond the Basics](https://www.youtube.com/watch?v=8peHqzO7oqE) (talk, 2021)
- [Micro Frontends and Moduliths with Angular](https://www.angulararchitects.io/en/ebooks/micro-frontends-and-moduliths-with-angular/) (ebook, 6th edition)
- [Modern Angular Architectures with Nx and Lightweight Stores](https://www.youtube.com/watch?v=Plsoiz1f6us) (talk, 2024)
- [Angular micro frontends — a modern approach to complex app development](https://angular.love/angular-micro-frontends-a-modern-approach-to-complex-app-development/) (article, 2024)

Authentication:
- [New RFC: OAuth 2.x for Browser-based Apps](https://www.youtube.com/live/mORR3hpMaJQ) (interview, 2024)

Design systems:
- [Implementierung mit Angular Material & Google’s Material 3](https://www.youtube.com/watch?v=h7zW9FCvU0A) (webinar 2024, part 1/3)
- [The big Angular UI library comparison](https://dev.to/kinginit/the-big-angular-ui-library-comparison-4ifp) (article, 2024)

## Human Resource/Time Estimation:

Number of sprints required: 1

Number of developers required: 3 (half-time)
