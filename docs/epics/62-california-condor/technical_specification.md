# DB Versioning (California Condor)
**Epic Type:** Implementation Epic

Epic planning and implementation follow the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/).

## Scope
### Outline:
This epic is for the implementation of the database versioning concept used to
transition data for a given database when a relevant schema change or systematic content
update occurs. Database versioning also provides a way to detect whether the current
database instance is the expected version or not. 


### Included/Required:
- Initial implementation on single service:
  - Add database version
  - Logic that checks database version at startup
  - Outer migration logic:
    - Locking mechanism
    - Start migration from detected version
  - Refinements and abstraction of common logic if applicable
- Apply database versioning to remaining services


## Additional Implementation Details:

### General Migration Logic

Each microservice has a database of its own, so any discussion of migrations can be
assumed to concern a single microservice. According to
[the ADR](https://github.com/ghga-de/adrs/pull/28), a given service will use a
single value to denote the version of its entire database, as opposed to versioning a
collection or the schema used for a document.

The *current* database version will be stored in a dedicated collection. The *expected*
database version will be stored in application code. When a service starts up, the
first action will be to compare the actual current version number against the expected
value. If the expected version number is not found in the database version collection
and the lock is not set, the service can start the migration process.

```json
// Database version collection upon migrating a database from version 1 to version 2:
[
  {
    "version": 2,
    "completed": ISODate("2024-11-18T09:30:00Z"),
    "duration_sec": 25
  },
  {
    "version": 1,
    "completed": ISODate("2024-10-07T09:00:00Z"),
    "duration_sec": 22
  }
]
```

The migration process will form a chain, where discrete migration logic exists for
every database version to migrate the data from version X to X+1. Most of the time, the
database will be current or, at most, one version behind. However, if a database restore
occurs and the data happens to be older, the migration process will begin at the
appropriate step in the migration chain and continue until the data is totally migrated.
Migration code should be preserved at least until there is no possibility of 
encountering the corresponding database version again. In the case that the database
version is *newer* than what it be, something has gone wrong *or* we have deployed
an older version of a service. The backwards case is treated just like the forward case:
the migration code will execute the backwards migration path if it exists and raise an
error if it doesn't.


### Services with Multiple Instances

Several services operate with more than one instance simultaneously because one serves
as a REST API and another consumes Kafka events (for example). We can also scale
services horizontally where there are multiple instances of a service running with the
same entrypoint (multiple Kafka consumers or multiple REST API instances). Only one
migration process should occur regardless of the number of instances in operation.
To make sure service instances don't trip over each other trying to run a migration,
we can "lock" the database to signal that there is already a migration in progress:

```
// locking collection with one document
[
  {
    "lock_acquired": true,
    "acquired_at": now,
  }
]
```

The first instance to obtain the lock is allowed to proceed, all others wait. This has
the benefit of preventing concurrent migrations if services are scaled. We need to
prevent race conditions when acquiring the lock itself, so we need to use a command like
[find_one_and_update()](https://pymongo.readthedocs.io/en/stable/api/pymongo/collection.html#pymongo.collection.Collection.find_one_and_update).
MongoDB ensures atomicity of document-level writes, so the first service granted write
access will update the document. The remaining simultaneous requests will not match
since the update request will filter for `"lock_acquired": False"`. When the query
returns `None` to the service code, the instance will know to wait for the pre-determined
interval before starting over with the initial DB version check:

![migration flowchart](./images/migration%20flowchart.png)

After preventing simultaneous migrations, we need to optimize how other instances
operate while a migration is underway and consider how to handle read and 
write requests. The outright simplest solution is to accept some downtime, take all
instances offline, and deploy the new version of the service(s) without any overlap.
Our database sizes are small enough that migrations should not take very long. We can
schedule updates for low-traffic times and even notify users beforehand if necessary.
If we determine that migrations take long enough that the above approach becomes
unrealistic, we'll have to take a more complicated approach.


### Reverse Migrations

There might be some situation where we need to apply the reverse of a migration.
If DB version 5 is applied, but we later find that we should have stayed with version 4,
then we need to move to version 6. Version 6 is not treated as some special 'undo'
version increment; the migration logic merely happens to move the data to the same
structure contained in version 4. However, in the case that we really just need to
deploy an older service version, the migration code needs to be able to perform
migrations from X to X - 1. The responsibility falls to the developer to ensure their
forward migration code has a backward counterpart, which should also be tested.

### Migration Code Organization

![Migration code organization](./images/migration%20code%20org.png)

In the image above, the green section indicates the top-level migration logic, most of
which can be implemented in a library like `hexkit`.  
The *rounded* orange boxes represent distinct migrations between database versions.  
The *square* orange boxes show common logic that can be abstracted into a library.  
The red-dotted items would be performed once for each batch of documents if a collection
were to be processed in batches.  
The gray box represents custom migration logic.  
This layout allows for simpler migrations to use migration framework code, but also
enables us to write the code we need for more complex migrations, like merging two
collections. The number of collections for any service is minimal, so there is no
need to automate or enforce iteration through collections. In fact, that would hinder
our ability to write migration logic involving multiple collections at once.

### Errors During a Migration

We can prevent database corruption from errors during migrations through the use of
temp tables and some renaming. Here's an example of how that looks while migrating a database containing two collections named `users` and `orders`:
1. Drop `tmp_users` and `tmp_orders` if they exist (maybe from previous failed attempt).
2. Create `tmp_users` and `tmp_orders`.
3. Read data from `users` and write new data to `tmp_users`.
4. Read data from `orders` and write new data to `tmp_orders`.
5. Rename `users` to `tmp_old_users` and `orders` to `tmp_old_orders`.
6. Rename `tmp_users` to `users` and `tmp_orders` to `orders`.
7. Apply the indexes from `tmp_old_users` and `tmp_old_orders` to `users` and `orders`.
8. Do some verification (count docs, examine content, double check indexes, etc.).
9. Drop `tmp_old_users` and `tmp_old_orders`.

If an error occurs at any point, drop all `tmp_` tables from this migration, log the
error, unset the lock document, make sure the old tables have the original names, and
exit.



### Testing Migrations

It's important that we test migrations thoroughly to avoid extended downtime from
unexpected errors.
Abstracted logic should be tested wherever it lives, like `hexkit`.
Tests should cover the following, but the list is not exhaustive:
- The locking mechanism
- Error handling
- Logging
- Database version detection
- Selecting the right migration to start with
- What to do when no matching migration exists

When we test individual migration code, like the code that will update collection A for
the migration from database version X to Y, we should use some mock data that represents
documents in the database.
Tests should at least verify that the migration code applies the right changes.


### Monitoring

Migration progress should be reported at periodic intervals, and the migration duration
should be both logged and stored in the database along with a timestamp so we can
identify performance issues early on. It makes sense to track the duration along with
database size so we can have a good estimate of how long upcoming migrations will take.


## Human Resource/Time Estimation:

Number of sprints required: 2

Number of developers required: 1
