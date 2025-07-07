# Refactoring Priorities (Nautilus)
**Epic Type:** Implementation/Exploratory Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).

**Attention: Please do not put any confidential content here.**

## Scope
### Outline:
This epic aims to explore and implement some of the refactoring priorities that are simple to implement
but give especially high benefits.


### Included/Required:
- replace dependency injection framework
- make devcontainer environment more lightweight
- streamline CI and local workflows


## Additional Details:

### Replace Dependency Injection Framework

Currently, we are using the dependency_injector library and are experiencing the following problems:
- difficult debugability:
    - e.g. if arguments are not passed correctly to the constructors, often the container just freezes without
    indications on where the problem is
    - the debugger cannot enter the cython code
- initialization does not happen lazy, i.e. event consumers are also started when starting the REST API of a service
- non-idomatic to python developers, initialization using constructers feels "magic" but unusual to new developers
- single developer, many open issues, maintenance unclear


Alternatives to evaluate:
1. do not use a DI framework at all but define one function that does the dependency resolution per entrypoint
   (i.e. one for the REST API and one for the event consumer)
2. [svcs](https://github.com/hynek/svcs) to evaluate both DI and service location (as alternative to DI)
3. [incant](https://github.com/Tinche/incant)

The conclusion should be documented in an Architecture Decision Record.

The solution will be implemented in the DCS as an example first before being propageted to other services.

### Make Devcontainer Environment More Lightweight

Currently, we are using the docker-in-docker feature of vscode to enable the execution of testcontainers inside
of the development container. This has the following disadvantages:
- disk space: each devcontainer contains a full copy of all the testcontainer images
- rebuild time: whenever you rebuild all testcontainer images are repulled slowing down the build process
  by several minutes
- security: the devcontainer has to run in elevated mode eliminating the security benefits of containerization

Alternatives to evaluate (https://code.visualstudio.com/remote/advancedcontainers/use-docker-kubernetes):
- Docker-from-Docker
- Docker-from-Docker-Compose

The conclusion should be documented in an ADR.

The solution will be implemented in the template repository and rolled out to all other repositories.

### Streamline CI and Local Workflows

Currently, developer workflows are partially implemented in local python scripts and partially in GitHub
actions. The following issues have been identified:
- there is no standard way of running the entire CI workflow locally with a single command
- Steps are highly redundant across Github Actions (e.g. the install of the package) increasing the execution time significantly
- the solution is not very adaptable, e.g. when certain checks are not required for a given repo

Alternatives to evaluate:
- running GitHub actions locally using [act](https://github.com/nektos/act)
- Represent the entire developer workflows (GitHub actions and scripts) in one local package e.g. using [invoke](https://www.pyinvoke.org/) 

A separate package might also be moved out of the microservice template repository and distributed via PyPI.

Moreover, the solution should also allow for easy configuration of which checks shall be run in which context, e.g. to
address different requirements of libraries vs. service or CI vs. local execution.

The solution will be prototyped in the DCS repository and distributed through applicable measure.

## Human Resource/Time Estimation:

Number of sprints required: 2

Number of developers required: 1.5
