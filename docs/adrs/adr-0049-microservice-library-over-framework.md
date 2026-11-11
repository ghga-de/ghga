---
status: accepted
date: 2022-03-24
tags: [backend]
---

# ADR-0049 — A library of building blocks instead of a microservice framework

## Summary

In the context of **sharing the generic, service-independent logic of the Triple Hexagonal Architecture between microservice codebases**

facing **the need to deliver fast coding progress while improving the development experience**

we decided for **a flexible library offering building blocks for microservice development**

and neglected **a prescriptive microservice framework**

to achieve **building blocks that developers use as far as they fit, and a library that grows incrementally without blocking service development**

accepting that **microservices may differ in structure and look, and developers face more choices than a framework would leave them**.

## Details

### Context

As discussed in the [Triple Hexagonal Architecture](https://ghga-de.github.io/ghga/hexkit/user-guide/arch_concepts/triple_hexagonal_arch.html) concept, the Triple Hexagonal Architecture has the potential to separate service-specific from generic and service-independent logic.
Here we discuss two different options for how this generic logic, which is represented by protocols and protocol providers (vocabulary described in the concept mentioned before), can be shared between microservice codebases: (1) a flexible library and (2) a prescriptive framework.

### Decision

We implement a general-purpose library that contains the most important building blocks for creating microservices.
This library became `hexkit` ([`libs/hexkit`](../../libs/hexkit/)).
The building blocks may comprise:

- Protocols (e.g. for event handling, RESTful query handling, object storage handling, CRUD database operations).
- Corresponding protocol providers (e.g. for Kafka-based event handling, documentation-driven Starlette-based REST APIs, CRUD MongoDB operations, etc.).
- Protocol providers for unit testing (mocks or very lightweight but functional implementations, e.g. acting only in local memory).
- Specifications for describing infrastructure states for specific protocols.
- A tool that can interpret these specifications to establish the specified state, e.g. in test and development environments as well as staging deployments.
- Pytest fixtures that establish the specified state and deliver preconfigured instances of protocol providers.
- Utilities for dependency injection that help with the handling of protocol providers and config parameters.

A framework, as described under [Alternatives](#alternatives), tends to be prescriptive and takes control over the microservice codebase.
By contrast, the library leaves the control with the microservice developer.
It only offers building blocks that a developer may use as needed and to the degree to which it makes sense for the specific microservice.
Moreover, the library may only recommend a certain structure for a microservice codebase; it does not (and has no means of) enforcing this structure.

Thus, a microservice developer might choose to rely only on a certain set of protocols and protocol providers from the library and ignore the available building blocks for other parts of the service.
For instance, the developer might use the building blocks for event handling and RESTful API provisioning, but decide to use a fully custom approach for talking to the database that might even deviate from the triple hexagonal design pattern.

In addition to the flexibility provided to the service developer, the development of the library itself is also simpler than that of a framework, as it relaxes the requirements regarding its feature completeness.
It is not a problem if the library does not satisfy all needs of a service.
Missing features can first be implemented directly in the service codebase and later be ported over to the shared library.
By contrast, a framework has to be much more feature-complete before being usable in service development.
In case of a missing feature, the development of dependent services is blocked until the feature is implemented in the framework.

### Consequences

Due to the given requirement of delivering fast coding progress, we have to balance the investment into the development experience and the time spent on implementing the actual business logic.
The library allows us to incrementally improve the development experience by adding new utilities and building blocks without slowing down the ongoing microservice development.
Eventually, once the library has matured, it can even be used as a basis for building a more strict microservice framework that further streamlines microservice development.

Until then, microservices do not necessarily look and feel the same, and developers have to make more decisions themselves.

### Alternatives

- **A prescriptive microservice framework**, which packages the shared logic and enforces a very well-defined structure onto microservice codebases.
  The restricted flexibility is linked with considerable advantages.
  Since the framework does not only recommend but enforces a specific structure, all microservices using it look and feel the same.
  This simplifies onboarding developers to new microservice repositories, and it is easier to guarantee a consistent user experience.
  The library leaves many decisions to the service developer, and the number of choices can be overwhelming.
  A framework offers a more focused experience in which the developer is only confronted with essential decisions.
  This can help reduce code complexity and cognitive load, making this option especially suitable for junior developers.
  We did not choose it because it has to be much more feature-complete before services can use it, which would slow down the ongoing microservice development.
