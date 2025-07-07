# Kafka Event Config Standardization (Oryx)
**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).

## Scope
### Outline:
We have different configuration key names that refer to the same topic or type in
different services, complicating the proper configuration of the services when they
are deployed jointly. To clarify,
"configuration" here means the various service-specific event publisher/subscriber
and config schemas defined in Python code, which contain
`"abc_topic"` and `"abc_type"` fields, *as well as* the values assigned for those
fields at runtime.

Example:  
When a user requests to download a file that's not yet in the outbox/download bucket,
the `DCS` fires an event to its *unstaged_download_event_topic*. The `IFRS` subscribes
to this topic, but the topic name is assigned to its config option labeled
*files_to_stage_topic*. Devs not familiar with this relationship between the two
services could be forgiven for not realizing that the two configured topics
are actually the same topic.
Ideally, both services will refer to this topic with identical configuration.
That is, the `DCS`'s config would also be named `files_to_stage_topic` (or vice-versa).

Thankfully the majority of configuration *does* use the same names, but the
issue can be completely resolved if we just standardize the config.
After all, if we can define a schema for a given Kafka event in a library, i.e.
`ghga-event-schemas`, then we can also define standardized config for the
corresponding event topic and type.

By storing this config schema in a central location, we also reduce change
propagation & maintenance costs in the potential event that we drastically
rework our use of Kafka. This could later be married with the currently dormant
`schema_registry` so Kafka-related domain concepts are fully co-located.


### Included/Required:
- Standardized Config in `ghga-event-schemas` and release
- Replace independent config implementations with the standardized versions
- Chart/diagram/map explaining config name changes (e.g. to help update PROD config)

### Not Included:
- Tie new standard configs to the corresponding schema definitions in `schema_registry`

## Additional Implementation Details:
We already have an unofficial document mapping the relationships between all
the various Kafka configurations, so this epic will lean on that information.
Developer review will help identify mistakes.

The config schema standardization process will involve three steps:
1. Identify existing Kafka pub/sub config schemas that refer to the same thing, i.e.
   the same topic & type.
2. Create a configuration class in `ghga-event-schemas` to standardize the config.
3. Update services to use the new standardized config schemas as appropriate.

The process will apply to all instances of Kafka event pub/sub config so that no
such config is defined outside of `ghga-event-schemas`. After all, if a service
publishes an event, presumably another service will consume that event, meaning they
will have to share configuration. If the schema is centrally defined, the config
should be too.

### A Note on "Normal" (non-outbox, e.g. stateless) Events Using the Outbox Pattern
We have events that don't communicate state but that nevertheless use the
outbox pattern solely for persistence. The motivation for storing these *stateless*
events is to aid in application restoration following the loss of Kafka data.
The *stateless* events that are persisted and published via the outbox pattern
always use the `upserted` event type, because deletion isn't an applicable
concept. The result is a "shoehorned" process that actually needs a dedicated
mechanism in `hexkit`. That mechanism, a class that mimics some of the outbox
DAO's functionality, can be created in another epic.


### Proposed Config Classes
> (stateful) means these events communicate state and should use the outbox pattern

> \* means the marked config naming has changed

<table>
<tr><th>New Config Class </th><th>Replaces </th></tr>
<tr>
<td><pre><code>
<strong>DatasetEventsConfig (stateful)</strong>:
   dataset_change_topic
   dataset_upsertion_type
   dataset_deletion_type
</code></pre></td>
<td><pre><code>
UMS:
  *dataset_deletion_event_topic
  dataset_deletion_event_type
WPS & DINS:
  dataset_change_event_topic
  dataset_upsertion_event_type
  dataset_deletion_event_type
Metldata:
  dataset_change_event_topic
  *dataset_upsertion_type
  *dataset_deletion_type
</code></pre></td>
</tr>

<tr>
<td><pre><code>
<strong>ResourceEventsConfig (stateful)</strong>:
   resource_change_topic
   resource_upsertion_type
   resource_deletion_type
</code></pre></td>
<td><pre><code>
Metldata & MASS:
  resource_change_event_topic
  *resource_upsertion_type
  resource_deletion_event_type
</code></pre></td>
</tr>

<tr>
<td><pre><code>
<strong>UserEventsTopicConfig (stateful)</strong>:
   user_topic
</code></pre></td>
<td><pre><code>
UMS & NOS:
  *user_events_topic
  (event type managed by hexkit)
</code></pre></td>
</tr>

<tr>
<td><pre><code>
<strong>FileMetadataEventsConfig</strong>:
   file_metadata_topic
   file_metadata_type
</code></pre></td>
<td><pre><code>
UCS:
  file_metadata_event_topic
  file_metadata_event_type
</code></pre></td>
</tr>

<tr>
<td><pre><code>
<strong>FileUploadReceivedEventsConfig</strong>:
   file_upload_received_topic
</code></pre></td>
<td><pre><code>
(each currently use hexkit's outbox pattern event type)
UCS:
  *file_upload_received_topic
IRS:
  *upload_received_event_topic
</code></pre></td>
</tr>

<tr>
<td><pre><code>
<strong>NotificationEventsConfig</strong>:
   notification_topic
   notification_type
</code></pre></td>
<td><pre><code>
NS & NOS:
  notification_event_topic
  notification_event_type
</code></pre></td>
</tr>

<tr>
<td><pre><code>
<strong>FileStagingRequestedEventsConfig</strong>:
   files_to_stage_topic
</code></pre></td>
<td><pre><code>
(both currently use hexkit's outbox pattern event type)
IFRS:
  *files_to_stage_topic
DCS:
  *unstaged_download_event_topic
</code></pre></td>
</tr>

<tr>
<td><pre><code>
<strong>FileStagedEventsConfig</strong>:
   file_staged_topic
   file_staged_type
</code></pre></td>
<td><pre><code>
IFRS:
  file_staged_event_topic
  file_staged_event_type
</code></pre></td>
</tr>

<tr>
<td><pre><code>
<strong>DownloadServedEventsConfig</strong>:
   download_served_topic
   download_served_type
</code></pre></td>
<td><pre><code>
DCS:
  download_served_event_topic
  download_served_event_type
</code></pre></td>
</tr>

<tr>
<td><pre><code>
<strong>FileDeletionRequestEventsConfig</strong>:
   file_deletion_request_topic
</code></pre></td>
<td><pre><code>
(each currently use hexkit's outbox pattern event type)
PCS, IFRS, DCS, & UCS:
  *files_to_delete_topic
</code></pre></td>
</tr>

<tr>
<td><pre><code>
<strong>FileDeletedEventsConfig</strong>:
   file_deleted_topic
   file_deleted_type
</code></pre></td>
<td><pre><code>
IFRS, DCS, & UCS:
  file_deleted_event_topic
  file_deleted_event_type
</code></pre></td>
</tr>

<tr>
<td><pre><code>
<strong>FileInterrogationSuccessEventsConfig</strong>:
   file_interrogations_topic
</code></pre></td>
<td><pre><code>
(all currently use hexkit's outbox pattern event type)
IRS & FIS:
  *file_upload_validation_success_topic
IFRS:
  *files_to_register_topic
</code></pre></td>
</tr>

<tr>
<td><pre><code>
<strong>FileInterrogationFailureEventsConfig</strong>:
   file_interrogations_topic
   interrogation_failure_type
</code></pre></td>
<td><pre><code>
IRS:
  *interrogation_topic
  *interrogation_failure_type
UCS:
  *upload_rejected_event_topic
  *upload_rejected_event_type
</code></pre></td>
</tr>

<tr>
<td><pre><code>
<strong>FileInternallyRegisteredEventsConfig</strong>:
   file_internally_registered_topic
   file_internally_registered_type
</code></pre></td>
<td><pre><code>
IFRS, DCS, IRS, DINS:
  *file_registered_event_topic
  *file_registered_event_type
UCS:
  *upload_accepted_event_topic
  *upload_accepted_event_type
</code></pre></td>
</tr>

<tr>
<td><pre><code>
<strong>FileRegisteredForDownloadEventsConfig</strong>:
   file_registered_for_download_topic
   file_registered_for_download_type
</code></pre></td>
<td><pre><code>
DCS:
  *files_to_register_topic
  *files_to_register_type
</code></pre></td>
</tr>

<tr>
<td><pre><code>
<strong>AccessRequestCreatedEventsConfig</strong>:
   access_request_topic
   access_request_created_type
</code></pre></td>
<td><pre><code>
NOS & ARS:
  *access_request_events_topic
  access_request_created_event_type
</code></pre></td>
</tr>

<tr>
<td><pre><code>
<strong>AccessRequestAllowedEventsConfig</strong>:
   access_request_topic
   access_request_allowed_type
</code></pre></td>
<td><pre><code>
NOS & ARS:
  *access_request_events_topic
  access_request_allowed_event_type
</code></pre></td>
</tr>

<tr>
<td><pre><code>
<strong>AccessRequestDeniedEventsConfig</strong>:
   access_request_topic
   access_request_denied_type
</code></pre></td>
<td><pre><code>
NOS & ARS:
  *access_request_events_topic
  access_request_denied_event_type
</code></pre></td>
</tr>

<tr>
<td><pre><code>
<strong>IvaChangeEventsConfig</strong>:
   iva_state_changed_topic
   iva_state_changed_type
</code></pre></td>
<td><pre><code>
NOS:
  iva_state_changed_event_topic
  iva_state_changed_event_type
UMS:
  *iva_events_topic
  iva_state_changed_event_type
</code></pre></td>
</tr>

<tr>
<td><pre><code>
<strong>SecondFactorRecreatedEventsConfig</strong>:
   auth_topic
   second_factor_recreated_type
</code></pre></td>
<td><pre><code>
NOS:
  *second_factor_recreated_event_topic
  second_factor_recreated_event_type
UMS:
  *auth_events_topic
  second_factor_recreated_event_type
</code></pre></td>
</tr>

</table>


## Human Resource/Time Estimation:

Number of sprints required: 1

Number of developers required: 1
