# Notification Orchestration Service (Kori Bustard)
**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).


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

| Recipient    | Purpose                                           | Data Required |
|--------------|---------------------------------------------------|---------------|
| User         | All IVAs invalidated                              | User ID       |
| User         | IVA verification code requested (Confirmation)    | User ID       |
| Central Data Steward | IVA verification code requested by user   | User ID       |
| User         | IVA verification code transmitted                 | User ID       |
| Central Data Steward | IVA verification code submitted by user   | User ID       |
| User         | 2nd Authentication Factor Recreated               | User ID       |


_**Data Submission**_

> Abbreviations:
> - RD: Research Data
>
> For the "Research data upload completion" notification, the Research Data Controller's
> email must be retrievable from the File ID.

| Recipient     | Purpose                         | Data Req'd |
|---------------|---------------------------------|------------|
| RD Controller | Research data upload completion | File ID    |



_**Data Request and Download**_

> Abbreviations:
> - DRR: Data Requester Representative
>
> If there is a stored entity linking the request to both the dataset and user IDs, then
> the request would be the only piece of information needed from the event.

| Recipient    | Purpose                         | Data Required      |
|--------------|---------------------------------|--------------------|
| DRR          | Request Created (Confirmation)  | Dataset ID, User ID|
| Data Steward | Request Created                 | Dataset ID, User ID|
| DRR          | Request Allowed                 | Dataset ID, User ID|
| Data Steward | Request Allowed                 | Dataset ID, User ID|
| DRR          | Request Denied                  | Dataset ID, User ID|
| Data Steward | Request Denied                  | Dataset ID, User ID|
| DRR          | Dataset ready for download      | Dataset ID, User ID|
| DRR          | *Data access expiration reminder| Dataset ID, User ID|
| DRR          | *Data access expired            | Dataset ID, User ID|

## Tasks/Additional Implementation Details:

The Notification Orchestration Service will use an event subscriber to consume events
from other services. Some of these events already exist, while others still
need to be defined and implemented. This approach ensures that microservices remain
agnostic to the notification framework. Instead, when a point in a user journey is
reached which merits a notification, the given microservice publishes an event with
the required details. That event is picked up by the NOS and used to construct
a notification event. In some cases, notifications may be sourced through other
means, such as the new outbox pattern, where database information is relayed through
an event that contains a subset of the database document's fields. For instance, a
change to a user's email field could be used to drive the creation of a notification.

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
hash key for each event and store in a database whether or not it was sent. However, a
hash key alone is not enough, since it is possible for two valid emails to a user to have
identical content. Another mechanism must be used to determine validity in such cases.
One candidate approach would be to use the correlation IDs to distinguish between true
duplicates (which should be blocked) and identical-but-distinct cases (which should be
sent).

### Addition of new event schemas to ghga-event-schemas

New event schemas must be added to ghga-event-schemas for notification sources which do
not already publish such an event (see tables above).

There are at least two fields that must be included in the outstanding events:
- `user_id`: string representing the unique user ID stored in the database
- `dataset_id`: string representing the accession number of a dataset

One model should be defined in ghga-event-schemas to encapsulate the User ID alone, since
that field is used across multiple events. The dataset ID is needed for the access
request details, so an AccessRequestDetails model should be defined as well.

The IVA notifications may require other information as details emerge, so required
information may be separately encapsulated for them.

### Replace ARS notification events

The Access Request Service currently publishes notification events to communicate the
status of access requests. The notification events should be removed, and the service
should instead publish the RequestCreated, RequestAllowed, and RequestDenied events.
The content of the notifications module can be moved to NOS.

## Human Resource/Time Estimation:

Number of sprints required: 2

Number of developers required: 1
