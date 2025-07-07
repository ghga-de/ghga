# Storing Data as strings vs BSON in MongoDB (Poodle Moth)
**Epic Type:** Exploratory Epic

Epic planning and implementation follows the
[Epic Planning and Marathon SOP](https://ghga.pages.hzdr.de/internal.ghga.de/main/sops/development/epic_planning/)

## Principle Components of Exploration:

We currently store data in MongoDB with a process that converts more complex data types,
such as datetimes, paths, and UUID objects, as their string representations.
More precisely, we perform `<model>.model_dump_json()` on the given pydantic model
before insertion. When the data is retrieved from the database, pydantic is able to
reconstruct the original model, e.g. a stringified UUID is converted to an actual UUID.

The above process is straightforward and uniform in its application, but introduces
drawbacks in the form of query complexity and reduced efficiency. MongoDB stores data
internally in a format called BSON (Binary JSON), which features support for many types
of data, like datetimes and UUIDs. Instead of storing the string representations of
such types, we could be storing them in, and querying with, their native format.

This epic will explore the tradeoffs between storing data as we do now (string format)
and migrating to BSON-supported formats. If we decide against storing data as BSON, we
need to decide whether we want to make the API a bit more consistent. Currently, the
filter mapping values are passed without being stringified, contrary to the values of
inserted or updated resources.

Results to be produced:
- ADR
- Implementation Epic & tasks (including migration tasks), only if BSON format is elected

- \<Provide a list here.\>

## Not part of this Exploration:

All aspects that shall be ignored during the exploration:

- Final implementation of the changes deemed necessary

## Material and Resources:

Materials to be studied (e.g. articles, book chapters, youtube videos, etc.) and any (external) persons/experts to talk to:

- [MongoDB Documentation](https://www.mongodb.com/resources/basics/json-and-bson)
- [BSON Documentation](https://bsonspec.org/)


## Human Resource/Time Estimation:

Number of sprints required: 1

Number of developers required: 1
