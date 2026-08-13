# GitHub Copilot Instructions for Epic Documentation

## Context

This repository contains technical specifications for GHGA (German Human Genome-Phenome Archive) development epics.

## Repository Structure and Naming Conventions

Each epic is documented in a directory with a filename consisting of the number and code name of the epic, separated by hyphens (e.g., `0-blob-fish/` or `77-alpine-longhorn-beetle/`).

See the `README` file in the root directory for all details.

## Document Structure

The documentation should contain the full title and type of the epic, its scope, implementation details and a time estimation.

There are two template directories:
- `template_exploratory_epic` for exploratory epics
- `template_implementation_epic` for implementation epics

The format and content of the technical specification are different depending on the epic type (exploratory or implementation). The structure of the documentation should follow these templates.

When creating new epics, always follow the structure of the respective template files in the repository and make sure to use a unique code name:

- Use `template_exploratory_epic/technical_specification.md` for exploratory epics
- Use `template_implementation_epic/technical_specification.md` for implementation epics

The main specification document should be always called `technical_specification.md`
like in the template. It starts with a summary of the goal that should be achieved with this epic. It lists all the anticipated features as well as which features should not be addressed as part of the epic. Furthermore, any results of the epics (such as documents, or code repositories) are linked here. On top of that, implementation details on how to reach the anticipated outcome/output of this epic are provided.

These template files contain the exact structure and placeholders that must be followed.

## Related Repositories

Most related repositories, particularly for the services and libraries developed by GHGA, can be found under https://github.com/ghga-de/.

Sometimes epics relate to Architecture Decision Records that can be found under https://github.com/ghga-de/adrs.

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
