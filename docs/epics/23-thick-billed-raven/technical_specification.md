# Integration of all File Services - Upload Stream (Thick Billed Raven)
**Epic Type:** Implementation Epic

The goal for this epic is to integrate all Backend File Services into the Testbed developed in [*19 - Pied Raven*](../19-pied-raven/technical_specification.md). This includes updating dependency versions in all services as well as ironing out possible differences in API usage and event processing to include the complete file upload path.

## Scope:
A scope definition can be found here: https://wiki.verbis.dkfz.de/pages/viewpage.action?pageId=220790885

## User Journeys

This epic covers the following user journeys:

### Integration of File Services (Upload Journey)

Integrate all File Services (UCS, IFRS, DCS) as well as the GHGA Connector into the already existing Testbed, containing the EKSS and IRS.

## RESTful API changes

The GHGA-Connector now sends the public key used in decrypting the crypt4gh header in the **POST** */uploads* API call.

The new OpenAPI doc can be found here:
[OpenAPI YAML](./api_definitions/ucs.yaml) - [Swagger UI](https://editor.swagger.io/?url=https://raw.githubusercontent.com/ghga-de/epic-docs/main/23-thick-billed-raven/api_definitions/ucs.yaml)

## Additional Implementation Details:

### All Services

- Update & cleanup dockerfiles to use only slim containers
- Update dependencies to the current version
    - ghga-chassis-lib
    - hexkit
    - ghga-event-schemas (Version 0.7.4 changed handling of datetimes)
### GHGA Connector

- The user now has to input a public key file for uploading a file. There could be a default setting.
- The **POST** */uploads* call transmits this public key

### UCS

- receive a public key in the **POST** */uploads* API call
- add the public key to the database (of the current upload attempt)
- once an upload has been received, send the public key with the *file_upload_received* event

### Testbed:

- Add GHGA-Connector, UCS, IFRS, DCS
- Add MongoDB instances for UCS, IFRS, DCS
- Add S3 bucket for permanent storage
- Add a complete testcase:
    1. create crypt4gh-encrypted file and public key, save unencrypted checksum and secret for later
    2. publish *metadata_submission_upserted* to be subscribed to by UCS
    3. send file and public key via GHGA-Connector to UCS
    4. wait for the *file_internally_registered* event
    5. check the following:
        - is the file in permanent storage?
        - is there an entry for the file in the IFRS DB?
        - is there an entry for the file in the DCS DB?
        - does the unencrypted checksum in the IFRS DB match the real checksum?
        - with the secrect id from the IFRS DB, check if the secret exists in vault and if it matches.


## Human Resource/Time Estimation:

Number of sprints required: 1

Number of developers required: 2
