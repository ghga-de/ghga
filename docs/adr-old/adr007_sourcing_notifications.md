# Sourcing Notifications

Date: 2024-01-29

## Summary

In the context of **sourcing and issuing notifications events in a microservice architecture**

facing **the need for a sustainable solution that minimizes maintenance costs**

we decided for **the addition of a new service responsible for sourcing notifications from published events**

and neglected **issuing notification events directly from separate microservices**

to achieve **clear separation of concerns at the microservice level, minimized change propagation,**
**and consolidated notification creation**

accepting that **the new service will be coupled to multiple other services**.

## Details

### Status

**accepted**

### Context & Requirements

  - "**Notification**" means the final entity which is emitted from the Notification Service, regardless of channel.
    - For the purposes of this ADR, a notification may be thought of as an email to the user.

  - "**Notification source**" refers to the reason a notification needs to be sent.
    If a file upload fails and a notification needs to be sent, the source is the failed file upload (and in code is the
    place where the microservice became aware of the failure). Publishing the notification "close to the source" would mean
    publishing a notification event directly from the same service where the file upload failure occurred.

  - "**Sourcing notifications**" means identifying notification sources in order to publish notification events.

  - "**Notification event**" refers to the `Notification` event type as defined in
    [`ghga-event-schemas`](https://github.com/ghga-de/ghga-event-schemas/blob/fc23f0a2fda44473ad5993ad592e2c9e7d642fed/src/ghga_event_schemas/pydantic_.py#L348).
    This is a command instructing a dedicated service to send a notification.

A microservice called the Notification Service currently exists with the functionality to send notifications, for example
via email, but it is not yet in use by the wider microservice ecosystem. The only action required to use this service is
the publication of a notification event, which is then consumed by the Notification Service. This approach is straightforward
but has drawbacks.

The main problem is that notification sources are distributed throughout services, meaning any systematic
change to notification events is then multiplied by the number of relevant services. That results in more reviews, more
opportunity for error, etc. For example, a small change such as updating all occurrences of "data steward" to use title
case ("Data Steward") in notification text could affect multiple repositories. That is not so bad if the changes are isolated,
but what if there is a large, mandatory template update which requires manual changes? The "simple" two-letter update evolves
into a larger PR with the potential for errors due to the required manual changes, meaning multiple reviews could be required.
This larger-than-expected PR must be repeated, too, for each service publishing notification events containing "data steward".

Thus, while publishing notification events close to the source seems convenient, it can become compounded by
orthogonal changes to the same repository/service. This kind of interference can mostly be mitigated
if the notification events are instead published by a dedicated service.

Additionally, it is reasonable to assume that the number of deployed microservices will increase over time as features
are added or expanded, further highlighting the need for a sustainable solution. Moreover, arbitrarily adding
notifications to a given service is an example of scope creep, which is important to avoid if we value microservices
with clearly defined responsibilities.

Moreover, many notifications require a contextual understanding of a larger user journey that goes far beyond the responsibility of a given microservice. E.g. the upload controller service has the sole responsibility of facilitating the upload of individual files. Once all uploads for a given submission have been completed, we might want to notify not only the uploading user but also all co-applicants of the submission and the responsible data steward. To do so context is needed on (1) which file uploads belong to a submission, i.e. when is a submission completely uploaded, (2) who is co-applicant to the corresponding submission, and (3) who is the responsible data steward. The upload controller service should not worry about any of that. Indeed, it does not even need to know that file uploads are grouped into submissions.

On the other hand, creating notification events separately from the source means that the service which *does* create
the notification events must possess some knowledge of, and is therefore coupled to, the source service.
It is conceivable that changes in a given microservice could create the need to modify this new notification-sourcing service.
For example, if functionality is removed or modified in such a way that the verbiage of a notification is no longer accurate.

### Decision

We propose designing and implementing a new microservice (name TBD) that solves the disadvantages of dispersed notification-sourcing
by centralizing that responsibility. This new service should observe events published by other services and determine when to create
a notification event. This will require no changes to the existing Notification Service. The exact implementation of the
notification-sourcing rules should be decided outside of this ADR.

### Consequences

The primary advantage of the new service is that the centralized control over notification events minimizes change propagation, maintenance costs,
and keeps microservices' responsibilities clearly defined. Testing should be easier, too, and prevents notification tests
from being added to services.

A fringe benefit is that developers won't need to spend time tracking down which service publishes a given notification event.

The tradeoffs are that the new service will be inherently coupled to other services, and any changes in a given microservice
which impact a notification source could *potentially* require changes in the new sourcing service. Fortunately, the relationship is
one-way: changes in the new sourcing service should not require changes to other services.
Creating notification events in an indirect manner also means there is a slight loss of context that will
necessitate extra diligence during development and testing.

### Alternatives

As an alternative, we could decide to adapt our event publishing mechanisms in required services and publish notification events directly.
This would be easier to implement in the short term, and the relationship between sources and resulting notification events would be clearer.
However, required maintenance in the long term would likely exceed what would be incurred by the proposed solution.
If the notification event needs to be restructured, then not only would the Notification Service need to be updated,
but so would every service that sends a notification. If notifications are implemented in one service but later deemed unnecessary,
then the service would probably need to be updated to remove the unused code (including tests).

If it was determined with reasonable certainty that only one or two kinds of notifications would ever need to be issued by GHGA,
then perhaps it would make more sense to publish the notification events directly.
