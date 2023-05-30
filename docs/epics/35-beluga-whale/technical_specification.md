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
    - Informing the Internal File Registry Service about the file stored permanently.
    - Creating an access claim for the file.
    - Priming the Work Package Service.
    - Creating a Work Package.
- Requesting the file download from the Download Controller Service.
- Verifying the publication of the expected `download_served` event.
- Requesting the envelope from the Download Controller Service.
- Decrypting the downloaded output file and comparing the checksum.
- Removing the test artifacts.


## Additional Implementation Details:

Before executing the tests, following setup should be achieved
- Set vault for user
- Set auth key
- Set signing key for Work Package Service
- Create storage buckets

## Human Resource/Time Estimation:

Number of week required: 2

Number of developers required: 2
