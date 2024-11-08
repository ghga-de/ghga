# DataPortal

This project was generated using [Angular CLI](https://github.com/angular/angular-cli) version 19.0.0-rc.0.

## Development server

To start a local development server, run:

```bash
ng serve
```

Once the server is running, open your browser and navigate to `http://localhost:8080/`. The application will automatically reload whenever you modify any of the source files.

## Code scaffolding

Angular CLI includes powerful code scaffolding tools. To generate a new component, run:

```bash
ng generate component component-name
```

For a complete list of available schematics (such as `components`, `directives`, or `pipes`), run:

```bash
ng generate --help
```

## Building

To build the project run:

```bash
ng build
```

This will compile your project and store the build artifacts in the `dist/` directory. By default, the production build optimizes your application for performance and speed.

## Running unit tests

To execute unit tests with the [Karma](https://karma-runner.github.io) test runner, use the following command:

```bash
ng test
```

## Running end-to-end tests

For end-to-end (e2e) testing, run:

```bash
ng e2e
```

Angular CLI does not come with an end-to-end testing framework by default. You can choose one that suits your needs.

## Additional Resources

For more information on using the Angular CLI, including detailed command references, visit the [Angular CLI Overview and Command Reference](https://angular.dev/tools/cli) page.

## Package Manager

This project uses pnpm to install dependencies which is a replacement for the much slower npm. Run 

```bash
pnpm install
```

to install the dependencies. It is important to note that you should not have a package-lock.json but instead a pnpm-lock.yaml. You can still use npm for run and other commands or to install global packages but not to add dependencies or to install all dependencies.

## Linter, Commits and Documentation

The repository is setup in such a way to only allow linted commits. That means, that commits are blocked by husky if they cause linter errors (currently, warnings are accepted). This ensures that code quality standards are maintained without build up technical debt that has to be fixed later on.

To ensure deterministic behavior, the pre-commit hook *does not* attempt to fix linter errors. Most of the time, you will be fine by simply running `ng lint --fix` which attempts to automatically fix most of the issues. If we ran that in the hook, however, you would be committing different code than the one you checked. So if you cannot commit your code, run lint fix. If that doesn't resolve all the issues (which you can see by running ng lint) resolve those issues and try again.

## Ease of use

For comfort, we are adding these shorthands: `npm run lint`, `npm run lf` (for `lint --fix`) and `npm run docs` (to build and serve the documentation). Apart from seeing the linter warnings when you (try to) commit or run the linter manually, your IDE should also show you these warnings in the code and fixing (the auto-fixable ones) should be offered in the context menu on hover or via Ctrl-..
