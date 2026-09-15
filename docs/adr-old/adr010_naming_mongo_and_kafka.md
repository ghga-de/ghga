# Naming conventions for Databases and Event Streams

Date: 2024-08-09

## Summary

In the context of **databases and event streams used in our microservices architecture**

facing **the problem that names for the same kind of objects were given inconsistently**

we decided for **the naming conventions listed below**

and neglected **other recommendations that can be found in the Internet**

to achieve **a consistent naming pattern that goes well with the used languages and the names we have been using so far**

accepting that **we may need to change some already established names to achieve this consistency**.

## Details

### Status

**accepted**

### Context & Requirements

We are currently using MongoDB for service databases and Apache Kafka for event streaming. For the integration of microservices, it is crucial that MongoDB database and collection names, as well as Apache Kafka topic and event type names, are configured correctly and consistently. Unfortunately, the names for these objects used in local and remote deployments, as well in the default and example configurations, were not consistent. Due to this inconsistency, it was often unclear whether composite names should be spelled in camelCase, kebab-case, or snake_case, leading to errors when the same object was spelled differently in two different service configurations. Therefore, we sought a consistent way to spell these names.

### Decision

**General Rules:**
- Stick to ASCII letters and digits. Start names with a letter.
- Use uppercase letters only where camelCase names are used as outlined below.
- Do not use blanks or special characters except underscores, hyphens and dots in some cases as outlined below.

**MongoDB Database Names:**
- Service databases should use the lowercase short form of the service name as the database name (e.g., "auth" for the authentication service or "wps" for the work package service).
- Do not append a "DB" suffix since it is redundant and the default databases don't use it either.
- Do not use dots in database names. Prefixes for test branches should be separated using a hyphen.

**MongoDB Collection Names:**
- The name should reflect the kind of entity stored in the collection.
- Use the plural form (e.g., "users" instead of "user").
- Avoid names with multiple components, but if needed, use camelCase (e.g., "accessRequests" instead of "access_requests" or "access-requests").
- Use dots for higher detail collections, e.g., "users.tokens" (though we prefer to include the details in the main collection).

**Kafka Topic Names:**
- Topic names should always be lowercase.
- Avoid names with multiple components, but if needed, use kebab-case (e.g., "access-requests" instead of "access_requests" or "accessRequests").
- Use dots if subtopics are needed, e.g., "files.deletions" (though we prefer a flat namespace for now).
- Prefixes for test branches should be separated using a hyphen, same as for database name prefixes.

**Kafka Event Type Names:**
- The event types should match the corresponding event schema class names but can be more specific.
- To distinguish them from the schema class names and since they usually correspond to Python methods, use snake_case for event types.
- They should follow a noun-verb format, with the verb usually in past tense (e.g., "searchable_resource_deleted").
- Use dots to specify domains, e.g., "auth.second_factor_recreated" (though we prefer to not include domains for now).

We currently do not reflect versioning in these names but may need to include versioning suffixes in these guidelines once we have clarified how to deal with event schema changes.

### Consequences

Adopting a naming convention will simplify service integration by providing a standardized way of spelling the different types of objects, thus avoiding mismatches. However, initially, we may need to rename a few items to achieve consistency.

### Alternatives

The guidelines listed above follow the recommendations found in the MongoDB and Kafka documentation and on StackOverflow.

Some alternative naming conventions are suggested in the Internet, such as using a "DB" suffix for database names or using PascalCase or camelCase for event types. We tend to avoid redundant suffixes, and prefer snake_case for event types, since they are already established in our code base and go well with the Python language used to implement the backend services.

## Links

- [MongoDB Naming Restrictions](https://www.mongodb.com/docs/manual/reference/limits/#naming-restrictions/)
- [Mastering MongoDB Collections](https://dev.to/mohitsinghchauhan/mastering-mongodb-collections-ei4)
- [Apache Kafka: Topic Naming Conventions](https://dev.to/devshawn/apache-kafka-topic-naming-conventions-3do6)
