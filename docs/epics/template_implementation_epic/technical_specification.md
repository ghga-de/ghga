# \<Epic Title\> (\<Epic Code Name\>)
**Epic Type:** Implementation Epic
  
**Attention: Please do not put any confidential content here.**

\<Please replace all appearances of `<...>`.\>

## Scope:
A scope definition can be found here: \<Insert Link to epic documentation on confluence.\>
## User Journeys

This epic covers the following user journeys:

\<Images and descriptions of user journeys go here. Images are deposited in the `./image` sub-directory.\>


![\<Example Image\>](./images/data_upload.jpg)

## User Journeys that are not part of this Epic:

- \<Provide a list here.\>


## API Definitions:

The definitions are hosted here:


\<Please list the APIs of all relevant services as demonstrated in the following: \>

### RESTful/Synchronous:

The RESTful service API are described using OpenAPI:


**\<Example Service\>**: [OpenAPI YAML](api_definitions/rest/example_service.yaml), [Swagger UI](https://editor.swagger.io/?url=https://raw.githubusercontent.com/ghga-de/epic-docs/main/template/api_definitions/rest/example_service.yaml)

(The OpenAPI specifications are hosted in the `./api_defitions/rest` sub-directory. Please make sure the links are pointing to the main branch, even if the file doesn't exist there because the PR has not being merged, yet.)

### Payload Schemas for Asynchronous Topics:

The payloads for asynchronous topics are described using JSON schemas:


- \<my_example_event_type\>: [JSON Schema](https://raw.githubusercontent.com/ghga-de/ghga-message-schemas/main/ghga_message_schemas/json_schemas/drs_object_registered.json)


(The JSON schemas should be defined in the following repository: https://github.com/ghga-de/ghga-message-schemas. Please insert only links from the main branch.)


## Additional Implementation Details:

- \<List further implemenation details here. (Anything that might be relevant for defining and executing tasks.)>


## Human Resource/Time Estimation:

Number of sprints required: \<Insert a number.\>

Number of developers required: \<Insert a number.\>
