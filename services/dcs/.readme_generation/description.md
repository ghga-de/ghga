This service implements the
[GA4GH DRS](https://github.com/ga4gh/data-repository-service-schemas) v1.0.0 for
serving files that where encrypted according to the
[GA4GH Crypt4GH](https://www.ga4gh.org/news/crypt4gh-a-secure-method-for-sharing-human-genetic-data/)
from S3-compatible object storages.

Thereby, only the `GET /objects/{object_id}` is implemented. It always returns
an access_method for the object via S3. This makes the second endpoint
`GET /objects/{object_id}/access/{access_id}` that
is contained in the DRS spec unnecessary. For more details see the OpenAPI spec
described below.

For authorization, a JSON web token is expected via Bearer Authentication that has a format
described [here](./dcs/core/auth_policies.py).

All files that can be requested are registered in a MongoDB database owned and
controlled by this service. Registration of new events happens through a Kafka event.

It serves pre-signed URLs to S3 objects located in a single so-called outbox bucket.
If the file is not already in the bucket when the user calls the object endpoint,
an event is published to request staging the file to the outbox. The staging has to
be carried out by a different service.

For more details on the events consumed and produced by this service, see the
configuration.

The DRS object endpoint serves files in an encrypted fashion as described by the
Crypt4GH standard, but without the evelope. A user-specific envelope can be requested
from the `GET /objects/{object_id}/envelopes` endpoint. The actual envelope creation
is delegated to another service via a RESTful call. Please see the configuration for
further details.
