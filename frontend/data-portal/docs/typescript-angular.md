# TypeScript and Angular Best Practices

How we write TypeScript and Angular in the data portal. These are style rules, read
when writing code, rather than the working rules in [AGENTS.md](../AGENTS.md).

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

## Angular Best Practices

- Always use standalone components over NgModules.
- Must NOT set `standalone: true` inside Angular decorators. It's the default in Angular v20+.
- Do NOT set `changeDetection: ChangeDetectionStrategy.OnPush` explicitly. `OnPush` is the default in Angular v22+.
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
- Prefer inline templates for small components
- Prefer Signal Forms (`@angular/forms/signals`) for new forms; when not using them, prefer reactive forms over template-driven forms
- Do NOT use `ngClass`, use `class` bindings instead
- Do NOT use `ngStyle`, use `style` bindings instead

## State Management

- Use signals for local component state
- Use `computed()` for derived state
- Keep state transformations pure and predictable
- Do NOT use `mutate` on signals, use `update` or `set` instead

## Templates

- Keep templates simple and avoid complex logic
- Do NOT call functions or methods in template bindings (including interpolation, `@if`/`@for` conditions, and inputs); bind to a signal or a `computed()` instead.
  - Why: template expressions are re-evaluated on every change detection cycle, so a function call re-runs each time regardless of whether its inputs changed. This is wasteful, scales poorly (worse inside `@for`), and gets more pronounced under zoneless change detection. Signals and `computed()` are memoized: they recompute only when a dependency actually changes, and they let change detection update only what changed.
  - Exceptions: pure pipes (also memoized) are fine, and event handlers (e.g. `(click)="doThing()"`) are calls in response to user actions, not evaluated during change detection, so they are fine too.
- Use native control flow (`@if`, `@for`, `@switch`) instead of `*ngIf`, `*ngFor`, `*ngSwitch`
- Use the async pipe to handle observables
- Do not assume globals like (`new Date()`) are available

## Services

- Design services around a single responsibility
- Prefer the `@Service` decorator for new singleton services in Angular v22+
- When not using `@Service`, use the `providedIn: 'root'` option for singleton services
- Use the `inject()` function instead of constructor injection
