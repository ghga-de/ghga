# Access Request Management Improvements (Ballan Wrasse)

**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://docs.ghga-dev.de/main/sops/sop001_epic_planning.html).

## Scope

### Outline

The goal of this epic is to improve the management of access requests by giving
data stewards control over the validity period and enriching the data access request with existing information (e.g., the corresponding DAC) and additional data entered
by the data stewards (e.g., reason for rejecting a request, internal notes, ticket ID).

### Included/Required

- Data stewards should be able to modify the requested validity period
  when the request is approved.
- Data stewards should be able to add a note to the requester
  (e.g., reason for denial of an access request or modified validity period).
- Data stewards should be able to add internal notes and the corresponding ticket ID
  associated with the request in the external help desk system.
- The data presented to the data steward in the access request manager
  and sent in the notification to the data steward should be enriched
  with existing information about the request and the dataset (e.g., DAC).
- When work packages are created, the validity period of the work package
  access token should be shown to the user.

### Not included

- Collecting additional context data for the request (e.g., affiliation).

## Affected services

- Access Request Service:
  - Allow changing the validity period in the PATCH request.
  - Allow adding/modifying external notes, internal notes, and ticket IDs.
  - Subscribe to dataset upserts and deletions, store the dataset title and DAC name
    in the access request, and change the state of deleted requests to "deleted."
  - Do not allow POST/PATCH requests for deleted datasets.
  - Provide the corresponding dataset title and DAC along with the request.
- Metldata:
  - The `MetadataDatasetOverview` event must be supplemented
    with the name of the corresponding DAC.
- Work Package Service:
  - Provide the validity period in the dataset list.
  - Provide the default validity period when creating a work package.
- Claims Service:
  - The internal API must provide the validity period instead of access yes/no.
- Data Portal:
  - Access Request Manager:
    - Allow data stewards to enter/modify external and internal notes.
    - Allow data stewards to enter a ticket ID or URL.
    - If a ticket ID is provided, automatically derive the ticket URL.
    - Allow data stewards to modify the validity period.
    - Show the internal and external notes in the details.
    - Show the ticket ID in the table.
    - Allow filtering by internal and external notes and ticket ID.
  - Work Package Creation:
    - Show the validity period of the access request after selecting the dataset.
    - Show the validity period of the work package access token after its creation.
- Notification Orchestration Service:
  - Enrich the access request-related notifications to data stewards
    with context information (e.g., name and email of the requester, request text,
    ID and title of the requested dataset, name of the corresponding DAC).

## Human Resource/Time Estimation:

Number of sprints required: 1
Number of developers required: 2
