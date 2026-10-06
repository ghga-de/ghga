---
name: data-portal
description: Use first for any change in frontend/data-portal/. Holds the portal's own Angular conventions and test rules, and wins where angular-developer disagrees.
paths: frontend/data-portal/**
---

# Data portal

`angular-developer` is Google's general Angular skill.
This one holds where the portal differs from it, or from the portal's own older code; where the two disagree, this skill and the docs it links win.

## Read first

- [`frontend/data-portal/AGENTS.md`](../../../frontend/data-portal/AGENTS.md) for commands, mocking and test levels.
- [`docs/typescript-angular.md`](../../../frontend/data-portal/docs/typescript-angular.md) before writing code; [`a11y-semantics.md`](../../../frontend/data-portal/docs/a11y-semantics.md) for templates and [`responsiveness.md`](../../../frontend/data-portal/docs/responsiveness.md) for layout.

## Where `angular-developer` does not apply

- **Commands:** the pnpm scripts and `just fe-*` recipes from `AGENTS.md`, never `ng test`, `ng e2e`, `ng serve`, `ng add` or `npm`.
  One spec runs as `pnpm ng test --watch=false --include <file>`.
  Validate with the smallest check that covers the change, not `ng build` after every edit.
- **Runtime config:** settings reach the app as `window.config`, which `run.js` writes to `public/config.js` from `data-portal.default.yaml`, and `ConfigService` (`src/app/shared/services/config.ts`) reads.
  A new setting goes into that YAML file, the `Config` interface and a `ConfigService` getter; there is no `src/environments` and no fetched `config.json`.
- **Forms:** new forms use Signal Forms (`@angular/forms/signals`), simple ones too; the template-driven forms in older code are not a model.
- **Template bindings:** no function or method call with an argument in a binding; derive the value in a `computed()` or a pure pipe, as `typescript-angular.md` says.
- **Unit tests:** `@testing-library/angular` with role and text queries, as the Playwright tests use, not component harnesses.
- **Styles:** component styles are SCSS (`angular.json`), with Tailwind classes in the template.
- **New projects and MCP setup:** not needed here; the `angular-cli` MCP server is configured in `.mcp.json`.

## Where the portal's code is not the model

Older code predates these rules; new code follows `angular-developer` here, even beside code that does not.

- New classes drop the `Component` and `Service` suffix: `DatasetFiles` in `dataset-files.ts`.
- New specs do not call `fixture.detectChanges()`; they await `fixture.whenStable()`, and route through the real router (Testing Library's `render` takes `routes`).
