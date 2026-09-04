# Node Runtime for the Angular project

Date: 2024-09-24

## Summary

In the context of **choosing a builder and package manager for the angular project**

facing **the need to have a smooth developer experience**

we decided for **to go with Node.js as a runtime environment and pnpm as a package manager**

and neglected **yarn, bun, deno, kuto and others**

to achieve **a good dev experience and reproducible builds**

accepting that **some additional performance improvements could be made by using a more experimental set of tools (like bun)**.

## Details

### Status

**accepted**

### Context & Requirements

There are two major building blocks: the JavaScript runtime environment and the package manager. For both, there are various options and they are somewhat mixed because the Node.js runtime environment comes bundled with the node package manager (npm) by default. Also, most package managers simply use the npm online package repository as a source for the dependencies to install.

### Decision

The field of JavaScript runtimes and package managers (with implications on developer experience, possible runtime performance in the case of SSR and execution times for pipelines) is wide, and there are many (sometimes very opinionated) projects. Making a good decision is important because switching the runtime later can be considerable work, and it impacts developer experience at a very fundamental level.

On the runtime side (that also includes the compiler / build process), there is the original default Node.js and many secondary ones that aim for individual goals (Deno - enhanced security, Bun - overall performance, LLRT - fast initial load, Kuto - smaller bundle size, etc.). At the time of writing, each of these runtimes implements a subset of the Node API, in line with its own design goals and target use cases. For a mainstream TypeScript stack like ours (test framework, many dependencies, linters etc.), that means a migration would carry a real risk of running into incompatibilities, in exchange for a comparatively small gain in build time. As a consequence, we should stick with Node.js (which offers the full Node API implementation) and accept that builds can take some seconds longer.

The package manager side is harder to decide. Typically, these package managers create a lockfile, to list the currently installed package versions. This can then be used to recreate the build. There are three main considerations:
1. The builds should be reproducible,
2. Installing the dependencies should work, i.e. the package manager should be able to resolve and successfully install our dependencies
3. The installation should be reasonably fast.

For our project, npm was the weakest option on all three points: we ran into lockfiles that did not fully pin our dependency tree, into cases where an install did not resolve correctly while other managers handled the same dependency set, and into the longest install times of the options compared here.

Bun comes with a package manager that succeeds on all of these points, but it is designed together with its own runtime environment, and we did not want to combine it with the Node.js runtime. Bun also does not execute post-install hooks by default, which some of our dependencies rely on and which is difficult to manage in a large codebase. Bun would be more interesting if we used [SSR](./adr017_server-side_rendering_in_angular.md) because its faster JavaScript execution would impact user experience. We have, however, decided not to use SSR.

pnpm and yarn are the two remaining options. For Yarn, the split between the v1 and the v2+ (Berry) line means that projects, tooling and documentation are spread over two rather different versions, which was the main drawback for us. pnpm also has an advantage in its way of handling mono-repos, and we therefore decided to use pnpm to install dependencies. For example, [here](https://refine.dev/blog/pnpm-vs-npm-and-yarn/#introduction).

### Consequences

Builds will likely be some seconds slower than if we used bun or others.

### Alternatives

These have been discussed above. The closest alternatives would have been yarn or possibly bun.
