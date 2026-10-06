# TypeScript and Angular best practices

How we write TypeScript and Angular in the data portal.
These are style rules, read when writing code, rather than the working rules in [AGENTS.md](../AGENTS.md).

## TypeScript best practices

- Use strict type checking
- Prefer type inference when the type is obvious
- Avoid the `any` type; use `unknown` when type is uncertain
- Use `undefined` for optional values and parameters and missing results or config settings, and `null` for explicit empty values, form and backend data and for resetting state.
- In case of doubt, prefer `undefined` over `null`, avoid allowing both unless really required.

## Documentation

JSDoc follows the [docstring rules](../../../docs/style.md#docstrings) of the Python side.

- All functions, methods, and classes require a JSDoc comment with a description line (enforced via eslint-plugin-jsdoc)
- Add `@param` and `@returns` tags only where the signature does not explain the value
- Keep JSDoc comments concise and meaningful - avoid redundancy with code that is self-explanatory
- Empty constructors are exempt from JSDoc requirements
- Arrow function expressions do not require JSDoc by linting rules; give one a JSDoc comment when it is not self-explanatory

## Angular best practices

- Always use standalone components over NgModules.
- Must NOT set `standalone: true` inside Angular decorators.
  It's the default since Angular v19.
- Do NOT set `changeDetection: ChangeDetectionStrategy.OnPush` explicitly.
  `OnPush` is the default in Angular v22+.
- Use signals for state management.
- Implement lazy loading for feature routes.
- Do NOT use the `@HostBinding` and `@HostListener` decorators.
  Put host bindings inside the `host` object of the `@Component` or `@Directive` decorator instead.
- Use `NgOptimizedImage` for all static images.
  - `NgOptimizedImage` does not work for inline base64 images.
- Do NOT invent Angular APIs or CLI behaviors.
  When uncertain, call `search_documentation` and cite Angular guidance in the response.
  That tool comes from the `angular-cli` MCP server, which reaches only a session started in `frontend/data-portal` (see [MCP tools](../AGENTS.md#mcp-tools)).

## Components

- Keep components small and focused on a single responsibility
- Use `input()` and `output()` functions instead of decorators
- Use `computed()` for derived state
- Put the template in a separate `.html` file; inline only a template of a few lines
- Use Signal Forms (`@angular/forms/signals`) for new forms, simple ones too; the template-driven forms in older code are not a model
- Do NOT use `ngClass`, use `class` bindings instead
- Do NOT use `ngStyle`, use `style` bindings instead

## Member visibility

Each visibility keyword has one job:

| Keyword     | Use                                                                                                 |
| ----------- | --------------------------------------------------------------------------------------------------- |
| `#name`     | Internal state and methods; JavaScript enforces it at run time                                      |
| `private`   | Internal, where Angular forbids `#`: a signal query such as `viewChild()` that only the class reads |
| `protected` | Members the template reads                                                                          |
| public      | The class API: inputs, outputs, service methods                                                     |

Since 22.2, Angular lets templates read `private` members, but we deliberately keep `protected` for them, as Angular's [style guide](https://angular.dev/style-guide) still recommends.
TypeScript does not see template reads, so a `private` member that only the template reads looks unused, and templates cannot read `#` fields in any version.
Revisit this if the portal turns on `isolatedDeclarations`, the setting that change was made for.

## State management

- Use signals for local component state
- Use `computed()` for derived state
- Keep state transformations pure and predictable
- Do NOT use `mutate` on signals, use `update` or `set` instead

## Templates

- Keep templates simple and avoid complex logic
- Do NOT call functions or methods in template bindings (including interpolation, `@if`/`@for` conditions, and inputs); bind to a signal or a `computed()` instead.
  - Why: template expressions are re-evaluated on every change detection cycle, so a function call re-runs each time regardless of whether its inputs changed.
    This is wasteful, scales poorly (worse inside `@for`), and gets more pronounced under zoneless change detection.
    Signals and `computed()` are memoized: they recompute only when a dependency actually changes, and they let change detection update only what changed.
  - Exceptions: pure pipes (also memoized) are fine, and event handlers (e.g. `(click)="doThing()"`) are calls in response to user actions, not evaluated during change detection, so they are fine too.
  - Reading a signal, `count()`, is no such call, and neither is the field state of a Signal Form, `form.email().invalid()`: both return a stored value.
- Use native control flow (`@if`, `@for`, `@switch`) instead of `*ngIf`, `*ngFor`, `*ngSwitch`
- Use the async pipe to handle observables

## Services

- Design services around a single responsibility
- Prefer the `@Service` decorator for new singleton services in Angular v22+
- When not using `@Service`, use the `providedIn: 'root'` option for singleton services
- Use the `inject()` function instead of constructor injection
