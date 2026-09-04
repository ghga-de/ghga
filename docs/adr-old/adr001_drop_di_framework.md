# Drop DI Framework

Date: 2023-10-23

## Summary

In the context of **dependency resolution inside of services**

facing **developer experience problems with our current DI setup, a custom wrapper around the `dependency_injector` library**

we decided for **an explicit dependency resolution based on basic async context managers**

and neglected **the dedicated frameworks svcs and incant**

to achieve **a simple, transparent, and debuggable setup**

accepting that **dependency resolution constructs may be verbose**.

## Details

### Status

**accepted**

### Context & Requirements

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

It is decided to realize dependency injection explicitly using standard python constructs
without a dedicated framework.

Explicit means that the dependencies are manually plugged together.

Usually it can be realized through the following setup:
- Write one async context manager that resolves the application core along with all its
  dependencies.
- Based on the core application resolver, write an additional async context manager
  per inbound adapter.

An example implementation can be found
[here](https://github.com/ghga-de/download-controller-service/blob/no_framework_di_prototype/src/dcs/inject.py).

### Consequences

Regarding our requirements, the chosen solution has the following advantages:

Since it is pure python, there is no magic involved and everything is transparent and
idiomatic to Python developers. Thus this is the ideal solution w.r.t. requirements 1 and 2.
Moreover, there is no external maintenance to worry about (requirement 3).
There are also no restrictions when it comes to the remaining requirements.

A potential downside is that there is no single dependency registry or container which
can be used for overriding dependencies during tests. However, in the past we have only
used this feature
[once](https://github.com/ghga-de/download-controller-service/blob/3d4f299bbecd414f1fafb6bfb1410cf2f91debdf/tests/test_edge_cases.py#L60).
There it was only used to reconfigure an already instantiated resource. A better solution was provided
as part of this
[PR](https://github.com/ghga-de/download-controller-service/pull/54/files#diff-203427ade0bdacb861392764efb874e6ce499a82b65c7cb4d9d0ac9543781665).

Even if an override cannot be avoided, it is still possible to just reimplement a test-specific
context manager for dependency resolution.

Moreover, it is not easily possible to access dependencies of the core application.
If this is required, the core provider could return a dataclass containing the core application
along with its dependencies instead of just the core application.

### Alternatives

We evaluated alternative DI frameworks, but we rejected them as we concluded that
the simplicity of the plain python solution outweighs the features of dedicated
frameworks. This is especially true for the small microservice code bases in which
explicit dependency resolution is not very labor-intensive and easy to oversee.

However, once our requirements shift, the conclusion might change. Thus we document
our findings for the evaluated frameworks as a starting point.

[SVCS](https://svcs.hynek.me/en/stable/index.html):
It is based on the principle of service location which
allows to only do the resource allocation if there is immediate need
for the resource. However, its documentation does not recommend going
all-in on the service location idea. Instead, it recommends doing the
service location in inbound hexagonal adapters (the example given are the
view functions of a Flask-like web framework, but the same could be done
e.g. in an event subscriber) and then injecting the dependencies into the
domain logic.
Thus, the full performance benefits of lazy resource allocation are not
guaranteed anymore. Moreover, the service location principle has the
disadvantage that mistakes in the dependency resolution become only
visible at runtime and only if the code performing the service location
is executed. By contrast, dependency injection unveils most problems
in static code analysis (if properly typed) or immediately during
service startup. Moreover, you can see the dependency injection in
inbound adapters as a violation of the Single Responsibility Principle.
By contrast, if you do dependency allocation directly where required
(the standard service location paradigm), requirement 4 is violated
as the service location would happen in the domain logic.
Moreover, it remains to be investigated whether providers for one
dependency may depend on providers for other dependencies.

[Incant](https://incant.threeofwands.com/en/latest/index.html):
It is a more traditional DI framework that supports two modes
for dependency resolution: (1) resolve by name (parameter name
must match the name of the provider) and (2) match by type.
The latter one has the advantage that it can help match abstract
types (protcols, ABC) to concrete implementations which could be
mapped to the protocol/provider pairs of the triple hexagonal
pattern. This is more concise than the chosen explicit resolution
but at the expense of being less transparent.
