# Basic User and Access Management (Royal Angelfish)

**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).

## Scope

### Outline:

Add modules to the GHGA data portal so that data stewards can perform the most essential tasks regarding the management of registered users and data access grants.

The UI should be similar to the already existing Access Request and IVA manager modules.

### Included/Required:

- User management page for data stewards in the frontend:
  - overview of all existing users with full name, email, roles and status
  - filters for all relevant fields (similarly to the Access Request Manager)
  - detail view that also shows their registration date, last status change, LS ID,
    IVAs, existing access grants and requests
  - It should be possible to deactivate and re-activate users (changing the status)
  - It should be possible to fully delete registered users
- Access grant management page for data stewards in the frontend:
  - list all existing access grants for datasets
  - filters for all relevant fields (particularly, dataset and user)
  - detail view that also shows creation date, validity period,
    potential revocation date as well as corresponding IVA and its state
  - also show corresponding access requests with details like creation date,
    request text, resolution date, ticket ID, DAC
  - revoke an existing access grant
- Necessary extensions to backend services to support the above pages

### Not included:

- Functions that require refined role concept and audit logging (see extensions below)

## User Interface

TBD

## API Definitions

The backend API does not yet provide the necessary information for the frontend to provide the specified functions. The following endpoints need to be added:

### Access Request Service:

- `GET /access-grants` - similar to existing `GET /access-requests` endpoint
- `DELETE /rpc/access-grants/{id}` - revoke an access grant

### Claims Repository:

- `GET /download-access/grants` - retrieve download access grants with optional query parameters for user ID, dataset ID, and validity period
- `DELETE /download-access/grants/{id}` - revoke a download access grant

### Endpoint Specifications:

The `GET` endpoints should return a list of all matching download access grants with:
- Corresponding user, IVA, and dataset IDs
- Validity periods and assertion dates
- Unique ID (matching the corresponding claim ID in the Claims Repository)

Claims with a revocation date set should not appear in the list of access grants.

The `DELETE` endpoints should *not* actually delete the corresponding claim, but instead set its revocation date.

The endpoints of the Access Request Service must require authorization as data steward. The endpoints of the Claims Repository are only internal and therefore do not need authorization. We should make the Claims Repository API more restrictive in the future (zero trust principle), but not as part of this epic.

### User Registry:

The User Registry already has an endpoint `PATCH /users/{id}` to deactivate and activate users and an endpoint `DELETE /users/{id}` to delete registered users.

## Notifications

The backend API must also send corresponding notifications to the users:
- when they are deactivated, re-activated or their account is deleted
- when any of their access grants is revoked

## Extensions

After we have refined the role concept to allow other elevated roles such as admin or superuser, and after implementation of an improved audit logging in our new  architecture, and after careful assessment of the security related and legal implications, we can consider a follow-up epic which would add the following functionality:

- As part of the user management, we could also
  - show roles and allow superusers to grant or revoke them
  - show an audit trail of past user activity.
- As part of the access management, we could provide superusers with a way to
  - modify the validity period of active or inactive access grants
  - create grants without access requests
  - allow already denied access requests, or
  - duplicate existing grants to cover additional datasets.

## Human Resource/Time Estimation:

Number of sprints required: 3

Number of developers required: 3
