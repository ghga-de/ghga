# Prepare for Federated Object Storage (Agile Wallaby)
**Epic Type:** Implementation Epic

## Scope

This epic aims to enhance existing functionality for all services that interact with S3 compatible object storage.
Currently, only communication with one configured object storage node is supported, but this should be extended to support multiple locations per service.

### Outline:

The proposed changes will touch the following services: Upload Controller (UCS), Interrogation Room (IRS), Internal File Registry (IFRS), Download Controller (DCS) and the event schema repository.

#### Common Service Changes:

The following configuration changes for object storage are proposed:
Moving from separate `access_key_id`, `secret_access_key` and `endpoint_url` for one storage configuration, a `s3_object_storages` object will now hold the configuration for all available locations.
Each location is identified by a label and the nested dict holds both the bucket name that shall be accessed as well as the credentials and endpoint URL for the specified bucket at the given location.

```
s3_object_storages:
    DKFZ:
        bucket: ghga_permanent
        credentials:
            s3_access_key_id: test
            s3_endpoint_url: http://localstack:4566
            s3_secret_access_key: '**********'
            s3_session_token: null
    Tuebingen:
        bucket: permanent
        credentials:
            s3_access_key_id: test
            s3_endpoint_url: http://localstack:4566
            s3_secret_access_key: '**********'
            s3_session_token: null
    ...
```

In addition to the already propagated bucket name, the `s3_endpoint_alias` is now propagated downstream in events and a corresponding field is populated in the respective databases.
This endpoint alias is a unique identifier for an object storage node, providing a 1:1 mapping to an endpoint URL.
It is assumed that files are never moved or copied across object storage nodes, just between buckets of the same location, i.e. the given endpoint URL is immutable across a file's lifecycle with respect to the location it is pointing to.

The proposed changes do not include redundancy across object storage nodes.

### Not Included:

Changes to the logic selecting which object storage node is chosen will not be addressed in this epic.

## Human Resource/Time Estimation:

Number of sprints required: 1-1.5

Number of developers required: 1
