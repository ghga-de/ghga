---
status: accepted
date: 2023-10-23
tags: [backend]
---

# ADR-0001 — Drop DI framework

## Summary

In the context of **dependency resolution inside of services**

facing **developer experience problems with our current DI setup, a custom wrapper around the `dependency_injector` library**

we decided for **an explicit dependency resolution based on basic async context managers**

and neglected **the dedicated frameworks svcs and incant**

to achieve **a simple, transparent, and debuggable setup**

accepting that **dependency resolution constructs may be verbose**.

## Details

### Context

Currently, we are using a wrapper around the [dependency_injector](https://github.com/ets-labs/python-dependency-injector)
library and are experiencing the following problems:

- difficult debuggability in our setup:
  - if arguments are not passed correctly to the constructors, we often saw the container stop without an indication of where the problem was
  - the debugger cannot step into the compiled Cython code
- initialization does not happen lazily when using our current wrapper, i.e. event consumers are also started when starting the REST API of a service
- the constructor-based initialization is not idiomatic for the Python developers on our team and feels "magic" to newcomers
- at the time of the decision, the library was developed almost entirely by a single maintainer, so the bus factor was a risk for us when depending on it long term

The ideal solution should:

1. be easy to learn, transparent (not-magic), and idiomatic to Python programmers
2. be easy to debug
3. be well maintained
4. not invade the domain code itself (e.g. through decorators), no changes
   in the core needed
5. support safe setup and teardown in async and sync execution mode
6. support object-oriented and functional paradigms
7. not require global state, the entire dependency injection must happen in
   function or method scope

### Decision

We realize dependency injection explicitly with standard Python constructs, without a
dedicated framework: the dependencies are plugged together by hand. Usually this takes:

- one async context manager that resolves the application core along with all its
  dependencies, and
- based on it, one additional async context manager per inbound adapter.

An example implementation can be found
[here](https://github.com/ghga-de/download-controller-service/blob/no_framework_di_prototype/src/dcs/inject.py).

### Consequences

Since it is pure Python, nothing is magic, and everything is transparent and idiomatic
to Python developers, which meets requirements 1 and 2 best. There is no external
maintenance to worry about (requirement 3), and no restriction for the remaining ones.

A potential downside is that there is no single registry or container for overriding
dependencies in tests. We had used this feature only
[once](https://github.com/ghga-de/download-controller-service/blob/3d4f299bbecd414f1fafb6bfb1410cf2f91debdf/tests/test_edge_cases.py#L60),
to reconfigure an already instantiated resource, and a better solution was provided in
this
[PR](https://github.com/ghga-de/download-controller-service/pull/54/files#diff-203427ade0bdacb861392764efb874e6ce499a82b65c7cb4d9d0ac9543781665).
Where an override cannot be avoided, a test can implement its own context manager for
dependency resolution.

Also, the dependencies of the core application are not easily accessible. Where this is
required, the core provider can return a dataclass holding the core application together
with its dependencies.

### Alternatives

We evaluated DI frameworks but rejected them, since the simplicity of plain Python
outweighs their features. This holds especially for small microservice code bases, where
explicit dependency resolution is little work and easy to oversee. If our requirements
shift, the conclusion might change, so we document our findings as a starting point.

[SVCS](https://svcs.hynek.me/en/stable/index.html): It is based on service location,
which allocates a resource only when it is needed. However, its documentation does not
recommend going all-in on service location. Instead, it recommends locating services in
inbound hexagonal adapters, such as the view functions of a Flask-like web framework or
an event subscriber, and injecting the dependencies into the domain logic from there.
That no longer guarantees the full benefit of lazy allocation. Service location also
means that mistakes in dependency resolution show only at runtime, and only when the
code locating the service runs, whereas dependency injection reveals most problems in
static analysis (if properly typed) or at service startup. Injecting dependencies in
inbound adapters can also be seen as violating the Single Responsibility Principle,
while locating them directly where they are needed, the standard service location
paradigm, violates requirement 4, because it happens in the domain logic. Finally, it
remains to be investigated whether providers for one dependency may depend on providers
for others.

[Incant](https://incant.threeofwands.com/en/latest/index.html): A more traditional DI
framework with two modes of dependency resolution: by name, where the parameter name
must match the name of the provider, and by type. Matching by type can map abstract
types (protocols, ABCs) to concrete implementations, which fits the protocol/provider
pairs of the triple hexagonal pattern. This is more concise than explicit resolution,
but less transparent.
