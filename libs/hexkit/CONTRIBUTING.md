# Contributing to hexkit

Thank you for your interest in contributing to hexkit!

Although hexkit is designed as a general-purpose library, it currently contains only
a limited collection of protocol-provider pairs that are of immediate interest to the
authors. We would like to add support for more protocols and technologies over time.

Feel free to develop hexagonal components yourself, whether or not you use the base
classes of hexkit. Not every protocol or provider has to be general-purpose, however,
if they are, please consider contributing them to hexkit.

## Development Environment

hexkit is developed in the [GHGA monorepo](https://github.com/ghga-de/ghga) under
`libs/hexkit`, together with the services that build on it. Apart from building the
docs, development tasks are run from the repository root rather than from this
directory.

For setting up the development environment, we rely on the
[devcontainer feature](https://code.visualstudio.com/docs/remote/containers) of VS Code.

To use it, you need Docker and VS Code with the "Remote - Containers" extension
(`ms-vscode-remote.remote-containers`) installed.
Then, you just have to open the monorepo in VS Code and run the command
`Remote-Containers: Reopen in Container` from the VS Code "Command Palette".

This will give you a full-fledged, pre-configured development environment including:

- all workspace members installed with their dependencies, plus the git hooks
- a Docker daemon inside the container, which the integration tests use to spin up
  their infrastructural dependencies (Kafka, MongoDB, S3, Vault) via testcontainers
- all relevant VS Code extensions pre-installed
- pre-configured linting and auto-formatting

If you prefer not to use VS Code, you can get a similar setup (without the editor
specific features) by installing [uv](https://docs.astral.sh/uv/) and
[just](https://just.systems/) and running the following in the repository root:

``` bash
just sync   # install every workspace member plus the shared dev toolchain
just hooks  # install the git hooks (the devcontainer does this for you)
```

Either way, the usual tasks are `just` recipes run from the repository root (see
[ADR-0015](../../docs/adr/0015-task-runner.md) for the full list):

``` bash
just test libs/hexkit  # run hexkit's test suite
just lint              # ruff check + format check across the workspace
just typecheck         # mypy, per workspace member
```

## Documentation

The narrative docs live under [`./user_guide`](./user_guide) and the site is
configured by [`./great-docs.yml`](./great-docs.yml); it is built with
[Great Docs](https://posit-dev.github.io/great-docs/), which uses Quarto. Neither is
part of the monorepo's shared toolchain — Great Docs requires Python >= 3.11 and is
only needed for the docs — so install both yourself, then build and serve the site
from this directory:

``` bash
# Install the docs toolchain (once)
uv tool install great-docs==0.14.1
# Quarto: see https://quarto.org/docs/get-started/

# Execute in libs/hexkit:

# Build the site into great-docs/_site/
great-docs build

# Serve the built site at http://localhost:3000
great-docs preview
```

`preview` only serves the existing build (it builds first only when no build exists
yet) and does not watch for changes. Because `great-docs build` clears and
regenerates the build directory, don't rebuild while a preview is running — instead,
after editing a page or `great-docs.yml`, stop the preview (`Ctrl+C`), re-run
`great-docs build`, and start `great-docs preview` again to view your changes.

> **Note:** great-docs' `build --watch` doesn't track edits to your
> `user_guide/` source (it only watches the generated build directory), so
> rebuild manually as above. A full rebuild takes a while, so don't expect
> your changes to show up immediately.

Note that hexkit's `README.md` doubles as the landing page of the
documentation site, so all links in it must be absolute URLs (repo-relative links
would break on the site).

## License

By contributing, you agree that your contributions will be licensed under the
[Apache 2.0 License](./LICENSE).
