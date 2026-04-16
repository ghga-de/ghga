# Agent Instructions for the Data Portal

This is the primary, tool-agnostic AI entrypoint for any coding agent working in this repository.

## Instruction source of truth

- `AGENTS.md` is the canonical AI entrypoint for this repository.
- `AGENTS.md` may reference additional project documentation (for example `README.md` and files in `docs/`) that is also authoritative and intended for both human developers and agents.
- Keep `.github/copilot-instructions.md` and `CLAUDE.md` short and focused on tool-specific notes that link back to this file.
- Avoid duplicating AI-specific guidance across files to prevent instruction drift; prefer linking from `AGENTS.md`.

## Prime Directive

- You are an expert in TypeScript, Angular, and scalable web application development.
- Write maintainable, performant, and accessible code.
- Follow Angular and TypeScript best practices.
- Prefer small, safe, reviewable diffs.
- Preserve existing architecture and patterns unless asked to change them.
- Optimize for correctness, maintainability, and testability over cleverness.

## Tech stack

- Angular and Angular Material: version 21
- TypeScript: strict
- Build: Angular CLI
- Styling: Tailwind CSS version 4
- State: Signals
- Unit testing: Vitest
- E2E testing: Playwright
- API mocking in development: Mock Service Worker (MSW)
- Lint/format: ESLint/Prettier

## Repo layout

- `README`: project description
- `docs`: developer documentation
- `src/app`: the Angular application code
- `src/mocks`: MSW handlers with static API/auth responses
- `tests`: end-to-end tests

## Repo commands (pnpm)

This repo uses `pnpm` (not npm) for dependency installation and scripts.

- Prefer pnpm scripts over direct CLI invocation for consistency with repo tooling.
- Dev server: `pnpm start`
- Build: `pnpm build` (or `pnpm watch`)
- Lint: `pnpm lint` (or `pnpm lf` to auto-fix)
- Typecheck (TS project refs): `pnpm typecheck` (or `pnpm typecheck:watch`)
- Typecheck incl. Angular templates: `pnpm typecheck:ng`
- Unit tests (Angular builder): `pnpm test` / `pnpm test:watch` / `pnpm test:ui`
  - Default: use `pnpm test`.
  - Do not run plain `vitest`; use Angular test commands only.
  - Use `vitest.fn()` for mocks (not `jasmine.createSpy()`).
  - For targeted runs, use `pnpm ng test --watch=false --include <file>` or `pnpm ng test --watch=false --filter <name>`.
  - Do not use argument forwarding (`ng test -- <runner-args>`) and do not duplicate watch flags across boundaries.
  - Invalid example (causes parsing failures): `ng test --watch=false -- --watch=false --include src/app/...`.
- E2E tests (Playwright): `pnpm e2e` / `pnpm e2e:ui` / `pnpm e2e:headed` / `pnpm e2e:debug` / `pnpm e2e:report`
  - Default command for e2e tests is always `pnpm e2e`.
  - Test framework: Playwright
  - Run individual tests with `playwright test TEST-FILTER`.
  - You don’t need to start the app manually; Playwright starts it via config in `playwright.config.ts`.
- Docs: `pnpm docs`
- README table of contents: `pnpm toc` (updates the region between `<!-- toc -->` and `<!-- tocstop -->`)

## Dev container CLI tools

The following tools are pre-installed in the dev container and available on `PATH`:

- `rg` (ripgrep): fast recursive text search; prefer over `grep` for workspace searches
- `fd`: fast file finder; prefer over `find` for file discovery
- `jq`: JSON querying and transformation (useful for inspecting `package.json`, `pnpm-lock.yaml`, etc.)
- `bat`: syntax-highlighted file viewer; drop-in alternative to `cat`
- `shellcheck`: shell script linter
- `shfmt`: shell script formatter

## Visual inspection

The dev server runs at **http://localhost:8080** (not the Angular default 4200).
The dev server must already be running (`pnpm start`) before attempting visual inspection.

VS Code's integrated browser gives agents full page interaction (read content, take screenshots, click, type, etc.) via built-in browser tools. There are two modes:

**Agent-opened pages** (isolated session — no cookies or login state):

- Use the `open_browser_page` tool with `http://localhost:8080`.
- Suitable for pages that don't require authentication.

**User-shared pages** (uses your existing browser session, including login state):

- The user must open the page in VS Code's integrated browser and click **"Share with Agent"** in the browser toolbar.
- Required for authenticated views (e.g. account page, upload grants list).
- `workbench.browser.enableChatTools` is already enabled in `.vscode/settings.json` — no setup needed.

For layout/visual tasks on authenticated pages, always ask the user to open the relevant page in VS Code's integrated browser and click **"Share with Agent"** before attempting to inspect or screenshot it.

## MCP tools

- MCP servers `angular-cli` and `context7` are available in this workspace.
- Prefer `angular-cli` for Angular-specific tasks: project/workspace discovery, Angular best practices, Angular documentation and examples, and Angular-focused migrations.
- Consult `angular-cli` before making assumptions about Angular APIs, templates, or CLI behavior.
- For `find_examples`, prefer `workspacePath` first for version-aligned results; if it returns no matches, rerun without `workspacePath` as a generic fallback.
- Use `context7` for non-Angular libraries and tooling (for example Tailwind, Playwright, Vitest, RxJS, and other ecosystem packages).
- Consult `context7` when external API behavior or recommended usage is uncertain, especially for version-sensitive questions.
- If external guidance conflicts with repository conventions, prioritize `AGENTS.md`, `README.md`, relevant files in `docs/`, and existing code patterns in this repository.

## Execution policy

- For code changes, run the smallest relevant validation first (targeted tests/lint/typecheck where possible), then run `pnpm test` as the default unit-test check.
- For documentation-only changes, test runs are optional unless requested.
- Prefer project scripts/tasks over ad-hoc commands.
- Do not create commits or branches unless explicitly requested.

## Generated artifacts

- Never manually edit generated output directories: `out-tsc/`, `playwright-report/`, and `test-results/`.
- Regenerate these artifacts using the appropriate scripts/commands instead.

## Required file headers

- New JavaScript/TypeScript modules must include the repository's required header block to satisfy ESLint rules:

```ts
/**
 * Short module description
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */
```

## TypeScript Best Practices

- Use strict type checking
- Prefer type inference when the type is obvious
- Avoid the `any` type; use `unknown` when type is uncertain
- Use `undefined` for optional values and parameters and missing results or config settings, and `null` for explicit empty values, form and backend data and for resetting state.
- In case of doubt, prefer `undefined` over `null`, avoid allowing both unless really required.

## Documentation

- All functions, methods, and classes require JSDoc comments (enforced via eslint-plugin-jsdoc)
- JSDoc must include `@param` for all parameters and `@returns` for non-void return types
- JSDoc must include a description line for the function/method/class
- Keep JSDoc comments concise and meaningful - avoid redundancy with code that is self-explanatory
- Empty constructors are exempt from JSDoc requirements
- Arrow function expressions do not require JSDoc by linting rules, but should still include JSDoc when the function is not self-explanatory and needs deeper explanation

Further project-specific development guidance:

- [Accessibility and Semantics Best Practices](docs/a11y-semantics.md)
- [Responsiveness Best Practices](docs/responsiveness.md)

## Angular Best Practices

- Always use standalone components over NgModules.
- Must NOT set `standalone: true` inside Angular decorators. It's the default.
- Use signals for state management.
- Implement lazy loading for feature routes.
- Do NOT use the `@HostBinding` and `@HostListener` decorators. Put host bindings inside the `host` object of the `@Component` or `@Directive` decorator instead.
- Use `NgOptimizedImage` for all static images.
  - `NgOptimizedImage` does not work for inline base64 images.
- Do NOT invent Angular APIs or CLI behaviors. When uncertain, call `search_documentation` and cite Angular guidance in the response.

## Components

- Keep components small and focused on a single responsibility
- Use `input()` and `output()` functions instead of decorators
- Use `computed()` for derived state
- Set `changeDetection: ChangeDetectionStrategy.OnPush` in `@Component` decorator
- Prefer inline templates for small components
- Prefer signal forms over reactive and template-driven ones
- Do NOT use `ngClass`, use `class` bindings instead
- Do NOT use `ngStyle`, use `style` bindings instead

## State Management

- Use signals for local component state
- Use `computed()` for derived state
- Keep state transformations pure and predictable
- Do NOT use `mutate` on signals, use `update` or `set` instead

## Templates

- Keep templates simple and avoid complex logic
- Use native control flow (`@if`, `@for`, `@switch`) instead of `*ngIf`, `*ngFor`, `*ngSwitch`
- Use the async pipe to handle observables

## Services

- Design services around a single responsibility
- Use the `providedIn: 'root'` option for singleton services
- Use the `inject()` function instead of constructor injection
