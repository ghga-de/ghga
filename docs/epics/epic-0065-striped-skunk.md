# Hexkit v4 Rollout (Striped Skunk)
**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).

## Scope
### Outline:
The release of `hexkit v4` necessitates updates to a number of GHGA repositories.

### Included/Required:
`ghga-service-commons` should be updated first because the current release requires
`hexkit < 4`, and many of the affected services use both `hexkit` and
`ghga-service-commons`. After updating and releasing the commons library, the following
services have to be updated (or their dependencies capped):
- `ars`
- `dins`
- `wps`
- `file-services-monorepo` (update all at once)
- `sms`
- `mass`
- `nos`
- `ns`
- `auth-service`
- `ghga-connector`
- `metldata`

### Optional:
- `wkvs` requires `hexkit`, but only for the configured logging. Nothing needs to be
done at the moment.
- `ds-kit`: Doesn't currently require functionality from `v4` and its dependency is 
  capped.


## Additional Implementation Details:

The MongoDB and Kafka providers and related protocols have changed the most, while
the S3 tools are more or less unchanged. 

### MongoDB Changes
`MongoDbDaoSurrogateId` has been removed, and `MongoDbDaoNaturalId` is named 
`MongoDbDao`. The protocol changes mirror this too: `DaoNaturalId` has been renamed
to `Dao`, while `DaoCommons` and `DaoSurrogateId` have been deleted.
If service code currently uses the Surrogate ID approach, it will be replaced with the
Natural ID approach. This can result in model consolidation since `v4` makes
creation models obsolete.

`MongoDbConfig` no longer has `db_connection_str`. Instead, it has `mongo_dsn`, which
is a type provided by `pydantic` for the same purpose with a touch more validation.
References will have to be updated, but usage is the same.
There is a new optional field called `mongo_timeout` that can be used to limit the
allowed duration of MongoDB operations. Especially useful for testing.

### Kafka Changes
The latest `hexkit` release includes functionality for the Dead Letter Queue (DLQ).
This mainly involves some tweaks to `KafkaEventSubscriber` and changes
to `KafkaConfig`, but there is also a new `DLQSubscriberProtocol` that will be used
in the DLQ Service. Service updates here are actually optional. To enable the DLQ in
existing services, their instance of `KafkaEventSubscriber` has to be retrofitted
with an event publisher. There should be at least 2 tests added for each service then:
1. Test that the service smoothly processes events from the `<service>-retry` topic
2. Test that the service correctly publishes problematic events to the DLQ topic

Given that the DLQ Service is still in development and that the DLQ updates in
`hexkit` are optional for services, it might make sense to defer the DLQ-specific
rollout. That would keep the PRs for this epic focused in scope.

## Human Resource/Time Estimation:

Number of sprints required: 1

Number of developers required: 1+ (the more the merrier)
