---
name: data-portal
description: Use first for any change in frontend/data-portal/. Holds the portal's own Angular conventions and test rules, and wins where angular-developer disagrees.
paths: frontend/data-portal/**
---

# Data portal

`angular-developer` is Google's general Angular skill.
This one holds where the portal differs from it; where the two disagree, this skill and the docs it links win.

## Read first

- [`frontend/data-portal/AGENTS.md`](../../../frontend/data-portal/AGENTS.md) for commands, mocking and test levels.
- [`docs/typescript-angular.md`](../../../frontend/data-portal/docs/typescript-angular.md) before writing code; [`a11y-semantics.md`](../../../frontend/data-portal/docs/a11y-semantics.md) for templates and [`responsiveness.md`](../../../frontend/data-portal/docs/responsiveness.md) for layout.

## Where `angular-developer` does not apply

- **Commands:** the pnpm scripts and `just fe-*` recipes from `AGENTS.md`, never `ng test`, `ng e2e`, `ng serve`, `ng add` or `npm`.
  One spec runs as `pnpm ng test --watch=false --include <file>`.
  Validate with the smallest check that covers the change, not `ng build` after every edit.
- **Runtime config:** settings reach the app as `window.config`, which `run.js` writes to `public/config.js` from `data-portal.default.yaml`, and `ConfigService` (`src/app/shared/services/config.ts`) reads.
  A new setting goes into that YAML file, the `Config` interface and a `ConfigService` getter; there is no `src/environments` and no fetched `config.json`.
- **Forms:** forms use Signal Forms (`@angular/forms/signals`), simple ones too.
- **Template bindings:** no function or method call with an argument in a binding; derive the value in a `computed()` or a pure pipe, as `typescript-angular.md` says.
- **Unit tests:** `@testing-library/angular` with role and text queries, as the Playwright tests use, not component harnesses.
  A spec that routes passes `routes` to `render` instead of stubbing the router.
- **Class names:** components and directives drop their suffix (`DatasetFiles` in `dataset-files.ts`); services keep `Service`, unless a name says better what the class does and clashes with no component, model or global (`Notifier`, `UploadBoxMappingStore`).
- **Styles:** component styles are SCSS (`angular.json`), with Tailwind classes in the template.
- **New projects and MCP setup:** not needed here; the `angular-cli` MCP server is configured in `.mcp.json`.
