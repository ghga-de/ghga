# Integration of Connector (CLI) with the Work Package Service (Purple Frog)
**Epic Type:** Implementation Epic

## Scope:

This epic covers integrating missing functionality to communicate with the work package service and process work package access and work order tokens in the GHGA Connector.

## Additional Implementation Details:

### API Calls

Two additional API calls to the work package service (WPS) need to be implemented, one to retrieve package information and one to retrieve work order tokens.
The first call replaces an existing function that currently gets its information from the config/environment variables.
API specs for the work package service endpoints can be found here: https://github.com/ghga-de/work-package-service/blob/main/openapi.yaml


### Work Package Access Token processing

The work package access token is an alphanumeric string that needs to be processed by the connector.
Due to security considerations the token should not be provided as command line option, as this would be included in the command line history.
Instead, the user should be asked for the token when needed.
This token is encrypted and needs to be decrypted before use and needs to be provided when calling the WPS to access package information and retrieve work order tokens.

### Work Order Token processing

A work order token needs to be retrieved each time a new pre-signed URL is generated and the expiry date needs to be checked and the token rejected if it is expired.

## Human Resource/Time Estimation:

Number of sprints required: 1

Number of developers required: 1
