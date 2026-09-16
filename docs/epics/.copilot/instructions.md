# GitHub Copilot Instructions for Epic Documentation

## Context

The `docs/epics` directory contains technical specifications for GHGA (German Human Genome-Phenome Archive) development epics.

## Structure and Naming Conventions

Each epic is named `epic-NNNN-<code-name>`, with the epic number padded to four digits and the code name in kebab-case (e.g., `epic-0000-blob-fish` or `epic-0077-alpine-longhorn-beetle`).

An epic without supporting files is a single Markdown file under that name (e.g., `epic-0093-giraffe.md`). An epic with supporting files is a directory under that name, holding the specification as `README.md` next to them (e.g., `epic-0019-pied-raven/README.md` next to `images/`). Start a new epic as a single file, and turn it into a directory in the same commit that adds the first supporting file, so a directory always means there is something else in it.

See the `README` file in this directory for all details.

## Document Structure

The documentation should contain the full title and type of the epic, its scope, implementation details and a time estimation.

There are two template directories:

- `epic-template-exploratory` for exploratory epics
- `epic-template-implementation` for implementation epics

The format and content of the technical specification are different depending on the epic type. The structure of the documentation should follow these templates; an epic that is half exploration and half implementation follows whichever fits better.

The three epic types are `Exploratory Epic`, `Implementation Epic` and `Exploration and Implementation Epic`. Every specification names its own on an `**Epic Type:**` line below the heading, and `just docs-check` rejects anything else.

When creating new epics, always follow the structure of the respective template files in this directory and make sure to use a unique code name:

- Use `epic-template-exploratory/README.md` for exploratory epics
- Use `epic-template-implementation/README.md` for implementation epics

The main specification document is the epic's own Markdown file, `epic-NNNN-<code-name>.md` or `epic-NNNN-<code-name>/README.md`. It starts with a summary of the goal that should be achieved with this epic. It lists all the anticipated features as well as which features should not be addressed as part of the epic. Furthermore, any results of the epics (such as documents, or code repositories) are linked here. On top of that, implementation details on how to reach the anticipated outcome/output of this epic are provided.

These template files contain the exact structure and placeholders that must be followed.

## Related Code and Decisions

The services, libraries and tools an epic describes live in the same monorepo, under `services/`, `libs/`, `tools/` and `frontend/`; the delivery side is in `deploy/` and `testbed/`.

Sometimes epics relate to Architecture Decision Records, which are in `docs/adrs`.

## Writing Guidelines

- The target audience are GHGA developers
- Use GitHub Markdown Flavor (GFM)
- Use clear, technical language
- Be precise and specific, but not overly verbose
- Include functional and non-functional requirements
- Use active voice where possible
- Use imperative mood for requirements
- Use bullet points for lists of tasks
- Reference related epics with relative links
- Link to other related documentation or repositories where this could be helpful
- Follow the structure defined in the templates
- Use consistent formatting and capitalization
- Use proper hierarchy (h1 = title, h2 = section, h3 = subsection)
- Include diagrams using Mermaid syntax when helpful
- Include specification of APIs and data schemas where needed
- Include migration paths for breaking changes
- Explain rationale for scope decisions when not obvious
- Be explicit about assumptions and constraints
- Clearly distinguish between "Included/Required", "Optional", and "Not included"
- Use "must", "should", "may" consistently (RFC 2119 style)
- Include security and performance considerations where applicable
