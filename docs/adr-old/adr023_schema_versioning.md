# Schema Versioning

Date: 2024-12-16

## Summary

In the context of **identifying which version of a Pydantic model was used to produce**
**a given database document or event, and identifying outdated data as early as**
**possible at runtime**

facing **the need for a standardized way to label Pydantic models in application code**

we decided for **versioning each service's entire database**

and neglected **relying on schema inspection, using a new database collection after**
**every schema update, appending version information to model class names, or**
**versioning each schema explicitly**

to achieve **a solution that is simple to implement, easy to maintain, unobtrusive**
**during typical development, and requires low commitment**

accepting that **we must take care to implement the solution consistently, that there**
**is no perfect way to prevent developer error, that some challenges may appear**
**when dealing with inheritance, and that we might need to deal with instances where**
**data adhering to an old schema definition crosses service boundaries**

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
  "Pydantic model", "model", and "schema" are used interchangeably here.
- ***Schema version***: A value that identifies a specific iteration of a schema,
  representing the exact data structure at a given point in time. Can be an integer,
  SemVer string, or similar incrementable value.

**Context**:
See [this write-up](https://www.mongodb.com/blog/post/building-with-patterns-the-schema-versioning-pattern)
by the MongoDB team to learn about a recommended approach to schema versioning in
MongoDB.

**Requirements**
- **Easy to maintain**: The solution should not burden developers or require frequent
  changes outside of the changes required when a schema update occurs.
- **Simple to implement**: We must implement the solution multiple times due to the
  microservice architecture, so it should not take long to add to an existing service.
  This is especially important when considering that some services manage more than one
  database collection (which corresponds to a single Pydantic model).
- **Unobtrusive**: The solution should not result in code littered with references to
  schema versions. Developers should not have to, e.g., explicitly include a schema
  version parameter for model instantiation.
- **Version ID Preservation**: The solution must provide a way for us to trace any data
  from a known Pydantic model back to the specific iteration of the model that was used
  to create the data. Without this mechanism, it will be very difficult or impossible to
  systematically work with data created with older versions of services.

### Decision

We will record a version number for each service's entire database. Migrations will
occur for every modified collection/schema *per database version*. Each database version
will correspond to a single service update or PR, but not every update or PR will
result in a database version bump. The database version number should be increased any
time that an update occurs to:
- a model inside the service which is used to store data in the DB
- a model outside of the service, but which is relied upon the service for storing data
  in the DB.

The database version number should be stored in code that is checked into VC (i.e. it
should not be a configured value).
When a service starts, the database version number can be checked. If the number in the
database is less than the version stored in code, the appropriate migration is run.

The database version number can be stored in a small 'changelog' collection containing
the date the database was migrated to each listed version number.

### Consequences

**Benefits**
- Easy to maintain -- just increment the database version number for a service when
  there is a change in a model used by the service.
- Quick implementation: The database version number and the logic for reading and acting
  upon it should be the same across services, allowing for copy and paste or using a service template. For the
  migration logic, some code may be eligible to be placed in a library such as
  `ghga-service-commons` or `hexkit` as appropriate.
- Unobtrusive: The database version number should not touch any of the rest of the
  service code.
- We can assume that every document in a service's database is using the latest schema
  definition.
- Low barrier to start using this solution and low commitment factor -- if we need to
  pursue an alternate approach, it should cost little to do so.

**Drawbacks**
- Inheritance: Some of our schemas are constructed via inheritance. If `SharedBaseModel`
  from `ghga-event-schemas` is subclassed by `ChildModel` in a service, then developers
  must be extra diligent to catch that change and apply the appropriate database version
  number and migration updates.
- It's difficult to tell if two services are using the same schema definitions without
  inspecting the code for each common model. We expect this to be checked as part of the
  verification done before a release, since such a mismatch would otherwise be hard to
  trace back to its cause.
- Recovery: If a document adhering to an outdated schema definition is encountered
  nonetheless, resolving it can be laborious. The best defense against this is to ensure
  that migrations are well written (e.g. idempotent) and thoroughly executed, and that all
  services are updated in lockstep when shared schemas are updated.

### Alternatives

**Neglected Path #1 - Implicit Versioning by Structure**
As recommended, for instance, by
[this SO user](https://stackoverflow.com/a/7251390/4187337).
Sometimes changes to document structures in document databases are handled without
explicitly labeling any versions. Outdated document data is detected by examining the
presence, absence, or content of given fields. For example, say documents with the
fields `title`, `author`, and `description` are used in an early version of an
application. One document might be:

```
{
    title: "The Final Empire"
    author: "Brandon Sanderson"
    description: "A ragtag group of rebels plot to overthrow an immortal tyrant in a world ruled by ash and mist."
}
```

After a time, the developers decide to split the author field into a first and last name.
The example becomes:

```
{
    title: "The Final Empire"
    author_first_name: "Brandon"
    author_last_name: "Sanderson"
    description: "A ragtag group of rebels plot to overthrow an immortal tyrant in a world ruled by ash and mist."
}
```

Regardless of whether the documents are updated upfront or lazily, the migration code
identifies the old documents by the *presence* of the `author` field or *lack* of
`author_first_name` and `author_last_name`. This approach takes advantage of the
schema-less design of document databases just like the chosen solution, but
relies on structural differences to identify old data. It works fine in simple
cases, but is error-prone, makes debugging harder, and can quickly bloat migration logic
as models and model changes become more complex.

**Neglected Path #2 - Semi-Explicit Versioning by DB Collection**
Another approach is to store documents in a new collection with each update to the
application-side schema. In the previous example, the first document might go into a
collection called `books_v1`. The documents following the second structure would go into
a separate collection called `books_v2`. This clearly delineates the
document evolution on the database side, and, presumably, the collection names are
tracked in version control for the application code. The latest collection is queried,
and data from old collections can be migrated to the newer one. However, the documents
themselves don't feature version information.

This approach works for standalone
applications, but it isn't well suited for design patterns that rely on shared schemas.
For us specifically, the models in `ghga-event-schemas` can change independently of
a given service. Without explicit schema version information, services are subject to a
variety of potential pitfalls in data validation, some of which might not raise an
error. Detecting incompatibilities would require schema inspection logic which is
duplicated for each service that uses the model. It's simpler for both services and
developers to ensure schema harmonization if there's an explicit value stamped on each
model.

**Neglected Path #3 - Explicit Versioning by Class Name**
We can version schemas by appending the version information to the class name and
renaming the class with each change. E.g., `User_v1`, then `User_v2`, and so on. It has
the advantage of being explicit and obvious to developers, and it also forces developers
to acknowledge when an upstream base class has changed. However, for models distributed
in shared libraries, it makes nearly every update a breaking update, and the version
information *still* isn't transmitted or stored alongside the data.

**Neglected Path #4 - Explicit Versioning Within Models**
A closely considered alternative was to add a `schema_version` field to each model as a
`Literal[<version>]`, using Pydantic's `frozen=True` and `init=True` to enforce the
current value and keep it hidden from development most of the time. The benefits to this
approach were that we would have robust confidence about the version of every document
stored in the database and could migrate documents on the fly if needed. It would also
provide the level of granularity required to ensure that every event payload and
document used to populate a Pydantic model is what it should be.

However, the
primary drawbacks are that it requires more maintenance than the chosen solution, is
significantly harder to turn back from if it turns out to be the wrong approach in the
long run, and opens the door for having collections featuring documents associated with
multiple schemas definitions rather than only the current schema. Not only that, but
adding the `schema_version` field to each model introduces the chance that the required
settings are incorrectly or not applied, defeating the purpose.

### Addendum

This has since been implemented in `hexkit`. A service declares the database version it
expects together with a map of migration definitions, which the `MigrationManager`
compares against the version recorded in the database when the service starts, applying
the outstanding migrations. Version 1 is reserved by the framework to mark the point at
which versioning was introduced.
