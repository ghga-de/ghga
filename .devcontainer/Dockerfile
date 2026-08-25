FROM mcr.microsoft.com/devcontainers/base:trixie

# A plain Debian base; both language stacks come from features (see devcontainer.json).
# Nothing installed here belongs to a stack — these are the tools that have to exist before
# any stack does, or that sit outside all of them.
#
#   python3 — the FULL metapackage, deliberately not python3-minimal, and distinct from the
#     interpreters the project builds against (uv owns those). This one exists because the
#     `image`, `demo-images` and `demo-load` recipes in the justfile, plus
#     scripts/image_members.py and scripts/affected_targets.py, invoke a bare `python3` and
#     `import tomllib` — they read pyproject/package manifests to decide what to build, so
#     they must run before and independently of any environment uv creates. Debian ships
#     tomllib in libpython3.13-stdlib and not in libpython3.13-minimal, and the node feature
#     installs python3-minimal on its own for node-gyp. Leaving this out therefore does not
#     give a missing `python3`; it gives one that is on PATH and fails at import time.
#   ripgrep, fd-find, bat, shellcheck, shfmt — working tools for the monorepo as a whole,
#     belonging to no stack in particular. rg and fd are how anyone, human or agent, reaches
#     a file in a tree this size without descending into node_modules and .venv (both honour
#     .gitignore, which is the whole point); bat and jq make what they find readable. Shell
#     is a first-class language here — the justfile's bash recipes, post-create.sh,
#     scripts/migration and testbed/scripts — and shellcheck and shfmt are what keep it
#     reviewable. jq belongs to the same set but already ships in the base image.
#   bind9-dnsutils — `dig` and `nslookup`, for a container whose name resolution is worth
#     interrogating by hand: /etc/hosts carries overrides from two directions (ghga-minio
#     via --add-host, the OIDC issuer host written by the data portal's run.js), the kind
#     cluster answers from its own CoreDNS, and --net=host puts all of it in one namespace.
#     Asking a named server directly is how you tell those apart. The docker-in-docker
#     feature happens to pull this in as well; it is declared here so the tool is a promise
#     rather than a side effect of someone else's dependency list.
#     Note this is a tool for people, not a scripting dependency — code that resolves a name
#     should use its own language's resolver, as run.js does.
# .github/workflows/ci.yaml (check-devcontainer) asserts this whole set on PATH.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      python3 \
      ripgrep fd-find bat shellcheck shfmt \
      bind9-dnsutils \
 && rm -rf /var/lib/apt/lists/*

# Debian renames these two to avoid clashing with fdclone and bacula-console-qt. Every
# command line anyone writes, copies, or remembers says `fd` and `bat`, so expose those.
RUN ln -s /usr/bin/fdfind /usr/local/bin/fd \
 && ln -s /usr/bin/batcat /usr/local/bin/bat
