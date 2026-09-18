# Agent Instructions for the Data Portal

This is the primary, tool-agnostic AI entrypoint for any coding agent working in this repository.

## Instruction source of truth

- `AGENTS.md` is the canonical AI entrypoint for this repository.
- `AGENTS.md` may reference additional project documentation (for example `README.md` and files in `docs/`) that is also authoritative and intended for both human developers and agents.
- `CLAUDE.md` beside this file is a stub pointing here and holds nothing else; Copilot is covered by the one `.github/copilot-instructions.md` at the repo root.
- Avoid duplicating AI-specific guidance across files to prevent instruction drift; prefer linking from `AGENTS.md`.
- [docs/agent-instructions.md](../../docs/agent-instructions.md) says what belongs in an `AGENTS.md`, a README, `docs/` or a skill. Keep always-on rules here and move longer task procedures into skills, which live in `.agents/skills/<name>/SKILL.md` and are symlinked into `.claude/skills/` until Claude Code reads the standard path.
- Copilot in VS Code finds this file through `chat.useNestedAgentsMdFiles`, set in the repo root's `.vscode/settings.json`; Claude Code finds it through the `CLAUDE.md` stub beside it.
- The dev container's CLI tools and the repo-wide rules are in the root [AGENTS.md](../../AGENTS.md).

## Prime Directive

- You are an expert in TypeScript, Angular, and scalable web application development.
- Write maintainable, performant, and accessible code.
- Follow Angular and TypeScript best practices.
- Prefer small, safe, reviewable diffs.
- Preserve existing architecture and patterns unless asked to change them.
- Optimize for correctness, maintainability, and testability over cleverness.

## Tech stack

- Angular and Angular Material: version 22
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

## API mocking philosophy

The MSW layer in `src/mocks` serves **static, pre-made responses only**. Do not write
mock handlers that contain backend logic. It backs both the dev server and the
Playwright tests, so this is also what bounds what those tests can prove — see
[Test levels](#test-levels) below.

- Reimplementing backend behaviour (filtering, pagination, sorting, validation,
  computed fields) duplicates work that already exists in the services, and the copy
  inevitably drifts from the real implementation. Tests then pass against a fiction
  and give a false sense of security. Real end-to-end coverage against actual backend
  is done in the [test bed](../../testbed/AGENTS.md).
- Add fixtures to `src/mocks/data.ts` and map them to endpoints in
  `src/mocks/responses.ts`. `createHandlersForResponses` in `src/mocks/handlers.ts` is
  the only handler generator; keep it generic.
- For endpoints that vary by query string, register one entry per request the app
  actually makes, including the query parameters:
  `'GET /api/ars/access-requests?dataset_id=<id>&*': someStaticResponse`. The handler
  picks the entry matching the most parameters, so a parameterless entry acts as the
  fallback.
- Deriving one fixture from another at module load (slicing an array into pages, for
  example) is fine — that is authoring data, not simulating a backend at request time.
- Paginated list endpoints are the one exception, since sorting and pagination are a
  convention shared by all of them rather than per-endpoint logic. A fixture with an
  `items` array registered _without_ `skip`/`limit` in its key is treated as the
  complete collection: the handler sorts it by `sort` (comma-separated fields, leading
  `-` for descending) and then applies `skip`/`limit`. Register the whole collection,
  not per-request pages — sorting must precede slicing, so an already-paged fixture
  cannot be sorted correctly. Do not extend this to filtering, validation, or computed
  fields.

## Test levels

Follows directly from the mocking philosophy above; see
[Automated tests](README.md#automated-tests) for the full rationale.

- **Unit tests** (Vitest, `*.spec.ts` next to the code): the default, and where most
  coverage belongs — request shapes, cache invalidation, state transitions, rendering
  and event wiring. Services are tested against `HttpTestingController`, components
  against mocked services.
- **E2E tests in this repo** (Playwright, `tests`): a **smoke layer**, despite the name.
  They stop at the network boundary, since the MSW mocks serve them too, but they boot
  the real app in a real browser with the real services and interceptors. Use them for
  assembly and wiring, not for behaviour. Keep them few and cheap.
- **Test bed** (`testbed/` in this monorepo): real backend and database, and the only
  level that can verify a flow whose outcome depends on the backend changing state.

The practical consequence: do **not** try to cover a "change something, then see the
change reflected" flow with a Playwright test here. The mocks answer identically before
and after the mutation, so such a test could only assert that a request was made — which
a unit test already does more precisely and far more cheaply. Leave those flows to the
test bed, which is more expensive to run.

## Repo commands (pnpm)

This repo uses `pnpm` (not npm) for dependency installation and scripts.

- Prefer pnpm scripts over direct CLI invocation for consistency with repo tooling.
- Install deps: `just fe-install` from the repo root (`pnpm install --frozen-lockfile`, as CI does), or `pnpm install` here when you are deliberately changing dependencies. `npm install` is blocked by the `preinstall` guard. The dev container installs them on create, together with Playwright's Chromium.
- Dev server: `just fe-dev` from the repo root, or `node run.js --dev` here. Not `pnpm start`: that runs `ng serve` without regenerating `public/config.js`, so the app is served with whatever runtime configuration a previous run left behind (or none at all). `--with-backend` / `--with-oidc` select the other three modes; see [Local development](README.md#local-development).
- Build: `pnpm build` (or `pnpm watch`)
- Lint: `pnpm lint` (or `pnpm lf` to auto-fix)
- Format: `pnpm format` (write) or `pnpm format:check` (verify)
  - Prettier runs standalone, not via ESLint; `eslint-config-prettier` only disables conflicting ESLint rules.
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
  - Prefer assertions on stable end states (URL/title/visible content) over transient intermediate states.
  - For known flaky UI transitions (menus/dialogs/navigation), use small bounded retries in shared test helpers rather than ad-hoc per-test logic.
  - Keep retries minimal (usually 1-2) and always keep a strict final assertion.
- Docs: `pnpm run docs` (use `run`; pnpm has a built-in `docs` command that would otherwise shadow the script)
- README table of contents: `pnpm toc` (updates the region between `<!-- toc -->` and `<!-- tocstop -->`)

## Visual inspection

The dev server runs at **http://localhost:8080** (not the Angular default 4200) and must already be running (`just fe-dev`). [Visual Inspection for Agents](docs/visual-inspection.md) has the two browser modes and when the user has to share the page.

## MCP tools

- MCP servers `angular-cli` and `context7` are available in this workspace (for Claude Code, only in a session started in this directory — see below).
- Prefer `angular-cli` for Angular-specific tasks: project/workspace discovery, Angular best practices, Angular documentation and examples, and Angular-focused migrations.
- Consult `angular-cli` before making assumptions about Angular APIs, templates, or CLI behavior.
- For `find_examples`, prefer `workspacePath` first for version-aligned results; if it returns no matches, rerun without `workspacePath` as a generic fallback.
- Use `context7` for non-Angular libraries and tooling (for example Tailwind, Playwright, Vitest, RxJS, and other ecosystem packages).
- Consult `context7` when external API behavior or recommended usage is uncertain, especially for version-sensitive questions.
- If external guidance conflicts with repository conventions, prioritize `AGENTS.md`, `README.md`, relevant files in `docs/`, and existing code patterns in this repository.

Claude Code and Copilot read different MCP config files, so this directory carries both:

- `.mcp.json` (key `mcpServers`) is Claude Code's config; `.vscode/mcp.json` (key `servers`) is Copilot's. They are kept separate on purpose — do not try to reconcile them into one.
- The two are not read alike. Copilot picks up the nested `.vscode/mcp.json` whichever folder the window is opened on, but Claude Code reads `.mcp.json` only from the directory the session starts in — so `angular-cli` reaches a session started here, and not one started at the repo root. That is deliberate: the server is of no use to backend work and the repo root carries no MCP configuration, so start Claude Code in this directory (the "frontend · data-portal" folder of `ghga.code-workspace`) when you want it.
- `.mcp.json` lists only `angular-cli`. `context7` is omitted there because Claude Code already has Context7 via the claude.ai-hosted connector, so the npx server would be redundant. (Copilot has no such connector, so `.vscode/mcp.json` lists both.)

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

## TypeScript and Angular style

TypeScript, JSDoc, Angular, component, state, template and service conventions are in
[TypeScript and Angular Best Practices](docs/typescript-angular.md). Read it before
writing code. Further project-specific guidance:

- [Accessibility and Semantics Best Practices](docs/a11y-semantics.md)
- [Responsiveness Best Practices](docs/responsiveness.md)
