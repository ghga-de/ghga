# MongoDB Migration Code Storage

Date: 2025-01-07

## Summary

In the context of **migrating MongoDB documents to align with evolving Pydantic models**

facing **the need for consistency between Pydantic models and MongoDB documents**

we decided for **implementing a migration process that is tightly integrated with service code**

and neglected **existing Python tools and centralizing all migration logic in a dedicated repository**

to achieve **simplified migration execution and minimal risk of errors from outdated documents**

accepting that **this approach involves some code redundancy and there is potential complexity in managing migrations across multiple services**.

## Details

### Status

**Proposed**

### Context & Requirements

**Definitions**
- ***Migration***: the modification of existing DB documents to make them compatible
with the current corresponding Pydantic model.
- ***Migration script***: some code that performs a migration to one or more
collections in the DB. Can be in Python or a MongoDB query.
- ***Migration process***: The process of running a migration script from start to
finish, including any work required to kick it off.
- ***Schema***: The schema of a Pydantic model (field names and types/definitions).
"Pydantic model" and "schema" can be used interchangeably.

**Context**:
MongoDB is a No-SQL database, meaning there are no rigid table schemas applied to data
stored within. In this case, table schemas (from SQL database design) correspond to the
schemas of the Pydantic models we use to represent structured data in application code.
This is very flexible and has a lot of benefits, but it also means that, without
proper planning, data structures can easily become inconsistent as the code evolves.
When using Pydantic models to define expected document structures in code, changes to
these models can lead to discrepancies between the models and the actual documents in
the database. This creates a need for migrations to ensure documents remain compatible
with the current models, and that services can process and validate the documents
correctly. Managing these migrations is critical for data integrity and avoiding runtime
errors due to outdated or incompatible documents.

**Requirements**
The solution should be easy to maintain, simple to implement, and convenient.
- **Easy to maintain**: The solution should not burden developers or require frequent
changes outside of the changes required when a schema update occurs.
- **Simple to implement**: We must implement the solution multiple times due to the
microservice architecture, so it should not take long to add to an existing service.
- **Convenient**: Once a schema and the corresponding migration script has been modified
and the code is moved to production, no further action should be required to execute the
database migration.

### Decision

For each service, we will include migration logic for each model that is stored in the
database. The migration logic for a service will run when the service is started so that
any outdated documents are updated before any business logic is performed.

### Consequences

**Advantages**:
The chosen solution features numerous benefits:
- The relevant Pydantic model(s) can be referenced in the migration code.
- The migration logic can be reviewed in the same PR that contains the schema change(s).
- The migration logic is kept with the service for which it's immediately relevant.
- No extra plumbing is needed to run the migration process.
- After a database restore, anomalies or outdated documents can be found and updated
automatically when a service starts up.
- The migration script has access to service config, so configured logging and DB
connections are available without writing new config.
- Migration scripts can be tested locally with less hassle.
- Can run migrations when an application is started. Because the code is located with
the service, there is the possibility to perform on-the-fly migration if appropriate.

**Disadvantages**:
The chosen approach has the typical microservice-related drawback where any changes we
decide to apply to the migration process as a whole must be rolled out to all affected
services. Likewise, there is some redundancy that is impossible to avoid. While not
much, the same boilerplate must be implemented in each affected service.

In select cases where 'fingerprinting', or storing a hash sum of a model's content, is
used, we will need to expend more effort to migrate data. This occurs at least in the
Notification Service (NS) and the Interrogation Room Service (IRS). The problem is that
the actual content is not stored, meaning we can't directly apply a migration script.
One solution here could be to remove the fingerprinting mechanism and store the actual
information. Please note that this problem exists independent of the chosen solution.

There is always the possibility for human error, even with multiple developers working
together. With some models referenced by various services, a service could be missed when
a shared model is updated. Such a case is expected to surface during testing before
release, and the DLQ mechanism provides a second line of defence against errors caused by
outdated documents.

Some services have both a Kafka consumer and a REST API, which run in separate
containers in the same pod. Both instances require the database to be up to date, but
it's not efficient to run the migration script more than once. If we run migrations
automatically at startup, we should add a mechanism to ensure that a migration script
is only triggered once for such services.

### Alternatives

The main alternative was to store migration scripts in a dedicated repository. This has
the benefits of staying out of application code and centralizing migration-related work,
but also has many drawbacks. For instance, script organization becomes a consideration.
If multiple services reference the same model, where do you store the related migration
code? There's also no direct access to the Pydantic models owned by
other services, meaning the model must be recreated and maintained in step with its
external counterpart. Automating migrations with this approach also requires extra work,
because there is no connection between a service and an arbitrary script in another
repository. Testing requires at least a basic re-implementation of the test code that
already exists in most services, too.

There exist some tools, like [pymongo-migrate](https://github.com/stxnext/pymongo-migrate),
but the schemas we maintain are fairly simple, and therefore so are the associated
migrations. According to its documentation, `pymongo-migrate` did not support
Python 3.12 at the time of writing, which we require. Other Python projects in this realm
include [mongodb-migrations](https://github.com/DoubleCiti/mongodb-migrations) and
[cikilop](https://github.com/skynyrd/cikilop), neither of which showed recent activity
at the time of writing.

### Addendum

The approach described here has since been implemented in `hexkit`, which provides a
`MigrationManager` along with helpers for defining the migrations of a service. The
database version reached is recorded in a separate versioning collection and checked when
a service starts up.

This also covers the open point mentioned above, namely ensuring that a migration is only
triggered once for services that run more than one container: the `MigrationManager`
acquires a lock in a dedicated collection before applying migrations, so that only one
instance carries them out.
