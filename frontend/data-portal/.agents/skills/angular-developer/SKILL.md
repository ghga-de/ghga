---
name: angular-developer
description: Use for Angular feature work, debugging, refactors, tests, or architecture questions in this repository. Applies Angular 22 and project conventions, and prefers MCP-backed Angular docs before making framework assumptions.
---

# Angular developer workflow for this repository

Use this skill when working on Angular code in this repository.

## Project baseline

- Angular and Angular Material are version 22.
- TypeScript is strict.
- State uses signals.
- Styling uses Tailwind CSS v4.
- Unit tests run through Angular's test builder with `pnpm test`.
- E2E tests use Playwright with `pnpm e2e`.

## Shared repo guidance

- Treat `AGENTS.md` as the primary shared instruction source.
- Check `README.md` and `docs/` when the task depends on repository-specific conventions.
- Keep diffs small, safe, and reviewable.

## Angular 22 conventions

- Use standalone components; do not add `standalone: true`.
- Do not set `changeDetection: ChangeDetectionStrategy.OnPush` explicitly; it is the default.
- Prefer signals, `computed()`, `input()`, and `output()`.
- Prefer Signal Forms for new forms. If not using Signal Forms, prefer reactive forms.
- Use the `host` property instead of `@HostBinding` or `@HostListener`.
- Use native control flow like `@if`, `@for`, and `@switch`.
- Do not use `ngClass`; prefer `class` bindings.
- Do not use `ngStyle`; prefer `style` bindings.
- Use `NgOptimizedImage` for static images.

## Tooling and validation

- Prefer MCP-backed Angular guidance and docs before assuming Angular APIs or CLI behavior.
- Prefer `pnpm` scripts over ad-hoc CLI commands.
- Validate changes with the smallest focused check first, then broaden only if needed.
- Use `pnpm test` as the default unit-test check when a task needs unit-test validation.
