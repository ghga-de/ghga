# Monorepo Setup for Multiple Microservices (Ethiopian Wolf)
**Epic Type:** Exploratory Epic

Epic planning and implementation follows the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/)

**Attention: Please do not put any confidential content here.**

## Principle Components of Exploration:

This epic aims at the establishment of a monorepo template that can be used to host
multiple microservices. Specifically, it shall satisfy the requirements imposed by 
our file-service setup and a microservice-based version of metldata.

Specifically, the following questions shall be answered:

- How to manage the life cycle of individual services? Specifically regarding versioning
  and releases.
    - We can start by evaluating whether a simple setup in which all services are
      versioned and released together is sufficient.
- How to manage dependencies for individual services?
    - One pyproject.toml and lock file per service?
    - One global lock file for keeping dependencies shared between services in sync?
    - One docker container per service?
- Overall directory structure? Clarifying where following files and directories are
  located:
    - src dirs for individual services
    - pyproject.tomls
    - example_config.yaml / config_schema.json
    - openapi.yaml
    - Readme(s) (per service or one global?)
    - scripts (e.g. update template script)
    - .devcontainer
    - python tooling settings (linters, formatters, etc.)
    - tests (unit, service-wise API testing, inter-service integration testing, etc.)
- Which types of tests are required in the mono-repo?
    - unit tests (per service)
    - service-wise API tests (conformance tests)
    - inter-service integration tests
        - Behavioral
        - contract-testing
        - black and/or white box
- How to ensure that microservice boundaries are respected?
    - import analysis?
    - flag PRs that add changes to multiple services within the monorepo
    - relying on discipline?
- How to deal with shared functionality?
    - e.g. in addition to services allow libraries in the monorepo
- Branching and release strategy?
- Is frontend part of a monorepo? I.e. vertical slice architecture?
    - In that case, how to manage authentication?


## Material and Resources:

Materials to be studied (e.g. articles, book chapters, youtube videos, etc.) and any (external) persons/experts to talk to:

- There is an existing [confluence page](https://wiki.verbis.dkfz.de/x/bwDYCg) listing
  the pro and cons of monoliths but also a list of resources.
- The [polylith architecture](https://polylith.gitbook.io/polylith) and associated
  [python tooling](https://davidvujic.github.io/python-polylith-docs/)
- Talk python episode about [monorepos in python](https://talkpython.fm/episodes/show/399/monorepos-in-python)
- Using [pants](https://www.pantsbuild.org/) as build system,
  [podcast episode](https://talkpython.fm/episodes/show/387/build-all-the-things-with-pants-build-system)
- Using [import-linter](https://github.com/seddonym/import-linter) to enforce
  microservice separation; article [here](https://www.piglei.com/articles/en-6-ways-to-improve-the-arch-of-you-py-project/)
- europython [talk on monorepos](https://www.youtube.com/watch?v=N6ENyH4_r8U)
- a tutorial on [using git for monorepos](https://www.atlassian.com/git/tutorials/monorepos)
- migrating from multirepos to monorepos:
    - discussion on
      [merging the git history](https://softwareengineering.stackexchange.com/questions/379228/steps-to-convert-multi-repo-to-mono-repo#:~:text=By%20default%20this%20will%20add%20the%20complete%20history%2C,updates%20from%20the%20original%20repo%20%28git%20subtree%20pull%29.)
      of multiple repos into one monorepo
    - https://medium.com/lgtm/migrating-to-the-monorepo-582106142654
- a [vscode-specific monorepo guide](https://github.com/microsoft/vscode-python/wiki/Mono-Repo-Set%E2%80%90up-Guide)
- an generally informative [website on monorepo tooling](https://monorepo.tools/)
- general articles:
    - https://medium.com/opendoor-labs/our-python-monorepo-d34028f2b6fa
    - https://medium.com/pinterest-engineering/building-a-python-monorepo-for-fast-reliable-development-be763781f67
    - https://medium.com/@davidsmithtech/dry-and-efficient-python-mono-repos-with-code-example-bc7ee8292e9d
    - https://betterprogramming.pub/the-pros-and-cons-monorepos-explained-f86c998392e1


## Additional Implementation Details:

Moving the existing file services into a monorepo might serve as a good proof of
concept as these services are fully evolved and understood.

Coming up with a strategy for life cycle management (versioning, releasing, branching)
has highest priority and should service a long-lasting solution. The other aspects are
less critical and might change in the future with preliminary solution being
acceptable. 


## Human Resource/Time Estimation:

Number of sprints required: 1

Number of developers required: 3
