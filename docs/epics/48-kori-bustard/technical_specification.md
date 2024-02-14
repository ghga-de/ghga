# Notification Orchestration Service (Kori Bustard)
**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://docs.ghga-dev.de/main/sops/sop001_epic_planning.html).


## Scope
### Outline:
The goal of this epic is to create a base implementation for a new service that
publishes notification events upon consuming events corresponding to specific points
in user journeys.
A description of the concept can be found in
[this ADR](https://github.com/ghga-de/adrs/blob/main/docs/adrs/adr007_sourcing_notifications.md).
The name of the new service is the **Notification Orchestration Service (NOS)**. It does
not replace or in any way supersede the similarly-named Notification Service. These are
two distinct services. The latter produces notifications, such as emails, from
consumed notification events, while the new NOS will be responsible for producing the
notification events. The relationship is effectively that the NOS sends commands to the
notification service in the form of notification events.

### Included/Required:
- Initial implementation of NOS
- Notification Service Idempotence
- Addition of new event schemas to ghga-event-schemas
- Replace ARS notification events


## Notification Summary:

### List of Notification Sources

The following list contains notifications and the intended recipients.
An asterisk by the Purpose field signifies that it's not clear whether the notification
is needed.

_**Authentication**_

> **IVA**, or **Independent Verification Address**, refers to some physical or digital
> address, such as a mailing address or phone number, and is used to issue a code for
> authentication.

| Recipient    | Purpose                               | Source Exists | Data Required |
|--------------|------------------------------------------|---------------|------------|
| User         | IVA invalidated                          | No            | User ID    |
| User         | IVA verification code requested (Confirmation) | No      | User ID    |
| Central Data Steward | IVA verification code requested by user  | No    | User ID    |
| User         | IVA verification code transmitted        | No            | User ID    |
| Central Data Steward | IVA verification code submitted by user  | No    | User ID    |


_**Data Submission**_

> Abbreviations:
> - DS: Data Steward
> - RD: Research Data
>
> For the "Research data upload completion" notification, the Research Data Controller's
> email must be retrievable from the File ID.

| Recipient     | Purpose                           | Source Exists | Data Req'd |
|---------------|-----------------------------------|---------------|------------|
| Central DS    | *Metadata is ready for review     | No            | File ID    |
| RD Controller | Research data upload completion   | Yes           | File ID    |
| RD Submitter  | *Approval/rejection of submission | No            | User ID    |



_**Data Request and Download**_

> Abbreviations:
> - DRR: Data Requester Representative
> - DACR: Data Access Committee Representative
>
> If there is a stored entity linking the request to both the dataset and user IDs, then
> the request would be the only piece of information needed from the event.

| Recipient    | Purpose                          | Source Exists | Data Required      |
|--------------|----------------------------------|---------------|--------------------|
| DRR          | Request Created (Confirmation)   | No            | Dataset ID, User ID|
| User (DACR)  | Request Created                  | No            | Dataset ID, User ID|
| DRR          | Request Allowed                  | No            | Dataset ID, User ID|
| User (DACR)  | Request Allowed                  | No            | Dataset ID, User ID|
| DRR          | Request Denied                   | No            | Dataset ID, User ID|
| User (DACR)  | Request Denied                   | No            | Dataset ID, User ID|
| DRR          | Dataset ready for download       | Yes           | Dataset ID, User ID|
| DRR          | *Data access expiration reminder | No            | Dataset ID, User ID|
| DRR          | *Data access expired             | No            | Dataset ID, User ID|

_**Data Deletion**_
| Recipient    | Purpose                     | Source Exists | Data Required |
|--------------|-----------------------------|---------------|---------------|
| Data Steward | Deletion request received   | Yes           | File ID       |


## Tasks/Additional Implementation Details:

The Notification Orchestration Service will use an event subscriber to consume events
from other services. Some of these events already exist, while others still
need to be defined and implemented. This approach ensures that microservices remain
agnostic to the notification framework. Instead, when a point in a user journey is
reached which merits a notification, the given microservice publishes an event. That
event is picked up by the NOS and used to construct a notification event.

### Initial Implementation

The initial implementation assumes that it has access to a database containing
documents storing required relationships:
- User ID to user email, full name, and title
- Dataset to Local Data Steward email, full name, and title
- Dataset to Research Data Controller email, full name, and title

**Structure**

The NOS will comprise four primary components:
1. An inbound adapter, an event subscriber, to consume notification source events
2. A core containing notification content and relevant logic
3. An outbound adapter for obtaining required information stored in the database
4. Another outbound adapter, an event publisher, to issue notification events

The body text used for notifications will be stored in templates that are part of the code in the git repository rather than configuration,
allowing for tighter control over public-facing content. While configuration is more
readily changed, it is crucial that changes to user notifications are reviewed and the
changes documented via version control.

The Central Data Steward email address could be stored in configuration, code, or
provided externally by the Well Known Values Service (WKVS). A decision on this specific
implementation detail is not urgent. For the initial implementation the Central Data
Steward email will be stored in configuration.

**Initial Notifications**

Rather than implementing all notifications immediately, a subset will be implemented
with this epic to allow for modifications. Once a satisfactory solution is agreed upon,
the remaining notifications may be implemented.
The ghga-event-schema changes could be completed first to widen the available selection.

### Notification Service Idempotence:

The Notification Service needs to maintain idempotence with regard to event processing,
yet ensure that notifications are issued once and only once. This requirement is not
met in its current state, where reprocessing a notification event would result in
multiple identical emails. One way to achieve this would be to generate a deterministic
hash key for each event and store in a database whether or not it was sent.

### Addition of new event schemas to ghga-event-schemas

New event schemas must be added to ghga-event-schemas for notification sources which do
not already publish such an event (see tables above).

There are at least two fields that must be included in the outstanding events:
- `user_id`: string representing the unique user ID stored in the database
- `dataset_id`: string representing the accession number of a dataset

The following should contain `user_id` and `dataset_id`:
- RequestCreated
- RequestAllowed
- RequestDenied

The following should only contain `user_id`:
- IVAInvalidated
- IVAVerificationRequested
- IVAVerificationTransmitted
- IVAVerificationSubmitted

### Replace ARS notification events

The Access Request Service currently publishes notification events to communicate the
status of access requests. The notification events should be removed, and the service
should instead publish the RequestCreated, RequestAllowed, and RequestDenied events.
The content of the notifications module can be moved to NOS.

## Human Resource/Time Estimation:

Number of sprints required: 2

Number of developers required: 1
