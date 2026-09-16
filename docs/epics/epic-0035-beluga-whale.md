# Archive Testing Framework - Happy Path (Beluga Whale)

**Epic Type:** Implementation Epic

## Scope

### Outline

This epic covers the implementation of the happy path for the file downloading functionality of GHGA Archive, utilizing all the necessary services.

### Included/Required

The epic includes:

- Development of a new testing framework [archive-test-bed](https://github.com/ghga-de/archive-test-bed), which is the successor to [file-stack-test-bed](https://github.com/ghga-de/file-stack-test-bed).
- Addition of Work Package Service and Claims Repository to the test framework.
- Removal of the file upload tests.
- Implementing the setup of the initial state for the file to be downloaded.
- Refactoring of the file download happy test case.

### Not included:

This epic does not include:

- Testing of the file upload
- Testing of unhappy test cases for file downloads.

## Testing Journey

This epic covers the following test journey:

- Setting the initial state for the file to be downloaded:
    - Creating staging, outbox and permanent storage buckets
    - Place a file in the staging storage bucket
    - Informing the Internal File Registry Service about the file stored permanently (event).
    - Creating an access claim for the file (REST call)
    - Priming the Work Package Service (event)
    - Creating a Work Package (REST call)
- Requesting the file download from the Download Controller Service (REST call via connector)
- Verifying the publication of the expected `download_served` event.
- Optional: Requesting the envelope from the Download Controller Service (REST call via connector).
- Optional: Decrypting the downloaded output file and comparing the checksum (using connector).
- Removing the test artifacts (via fixtures).


## Additional Implementation Details:

Before executing the tests, following setup should be achieved
- Create storage buckets
- Set vault AppRole for Encryption Key Store Service
- Set auth key
- Set signing key for Work Package Service

Cleanup after test:
- Extend existing fixtures to clean up the test state after executing:
  - for MongoDB, drop used database
  - for s3 delete used buckets
  - for kafka delete used topics


## Human Resource/Time Estimation:

Number of week required: 2

Number of developers required: 2
