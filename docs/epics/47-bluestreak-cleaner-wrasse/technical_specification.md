# Automatically remove stale content from buckets (Bluestreak Cleaner Wrasse)
**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).


## Scope
### Outline:

This epic aims to provide mechanisms to remove no longer needed objects from intermediate object storage buckets, i.e. every bucket except the permanent one.
To this end, two questions have to be solved for each bucket:
 - Which service is responsible for cleaning which bucket?
 - How is the cleaning job initiated, i.e. by event or periodically?

### Included/Required:

#### Datasteward Kit:
Functionality to actually call the PCS and request file deletion is not yet implemented.
The DS-Kit should be the correct place for this and a new (sub)command exposing this functionality should be made available in `cli/file.py`.
A delete call needs to be made to the `files/{file_id}` endpoint, which is documented here: https://github.com/ghga-de/purge-controller-service/blob/ac58b0dd2d7d8725ce2c387e331d19f27e6c2c5d/openapi.yaml.
Authorization should use the token mechanism already implemented in the DS-Kit, but a separate and distinct token.

#### Upload Controller:
Currently, incoming data accumulates in the inbox bucket. Instead, data should be removed asap, once it's no longer needed during upload. This should be handled when receiving the validation success/failure event (https://github.com/ghga-de/ghga-event-schemas/blob/fc23f0a2fda44473ad5993ad592e2c9e7d642fed/src/ghga_event_schemas/pydantic_.py#L182-L269) from the interrogation room.

Additionally, a periodic job should check if files remain in the inbox that are no longer needed and (for now) log affected objects. As objects should be purged asap, objects remaining in the bucket for an accepted/rejected/cancelled upload mean there is probably a logic bug somewhere.

As the upload controller holds some file data and metadata, the event subscriber needs to be extended to consume file deletion request events from the purge controller (https://github.com/ghga-de/ghga-event-schemas/blob/fc23f0a2fda44473ad5993ad592e2c9e7d642fed/src/ghga_event_schemas/pydantic_.py#L374-L383).

#### Interrogation Room:
Currently, incoming data accumulates in the staging bucket. Instead, data should be removed asap, once it's no longer needed during upload. This should be handled once the file is successfully registered and moved by the internal file registry. This means the IRS needs to listen for the file internally registered event (https://github.com/ghga-de/ghga-event-schemas/blob/fc23f0a2fda44473ad5993ad592e2c9e7d642fed/src/ghga_event_schemas/pydantic_.py#L272-L275).

Additionally, a periodic job should check if files remain in staging, that are no longer needed and (for now) log affected objects. As objects should be purged asap, objects remaining in the bucket mean there is a probably a logic bug somewhere.

The interrogation room stores no relevant file data or metadata and needs no consumer or endpoint for purge controller interaction.

#### Download Controller:
The download controller already has functionality to respond to PCS events and a periodic cleaning command for the outbox.
However, the cleaning command only takes into account one given bucket and should perform the job for all its configured buckets instead.


## Human Resource/Time Estimation:

Number of sprints required: 1

Number of developers required: 1
