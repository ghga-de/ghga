# epic-docs
Documentation and plans for service development epics.

## Structure:

Please follow the following directory structure:
- `{epic_number}_{epic_name}` - one top level directory per epic
    - `api_definition` - contains all API specs
        - `rest` - RESTful API specs as OpenAPI3-compliant YAMLs
        - `message_topics` - JSON schemas for the content of each messaging topic
    - `mocks` - Any kind of mock documents, e.g. mock JSON responses from a RESTful API
