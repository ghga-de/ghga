# Integration of all File Services - Download Stream (Common Raven)
**Epic Type:** Implementation Epic

The goal for this epic is to integrate all Backend File Services into the Testbed developed in [*19 - Pied Raven*](../19-pied-raven/technical_specification.md). This epic builds on [*23 - Thick-Billed Raven*](../23-thick-billed-raven/technical_specification.md) and aims to bring the Testbed to completion by including the complete file download path and changes required to make everything work according to the arch-concept.

## Scope:
A scope definition can be found here: https://wiki.verbis.dkfz.de/x/MIBSDQ

## User Journeys

This epic covers the following user journeys:

### Integration of File Services (Download Journey)

Produce a script to test the download path in the testbed and adapt the DCS and IFRS to allow for a fully functionioning download path.

## Additional Implementation Details:

### IFRS
- The IFRS needs to consume the *NonStagedFileRequested* event, stage file to outbox and emit the *FileStagedForDownload* event afterwards

### IFRS/Hexkit
- Implement multipart copy with offset to store file object without envelope in permanent storage

### DCS
- Adapt to request envelope from EKSS and serve the assembled file (envelope + encrypted file content) using custom download ranges

### Testbed:

- Add a test script for the download path
    1. Run upload path script to populate permanent storage and IFRS state
    2. Request a file download through the ghga-connector
    3. Check for download staging events happening
    4. Verify the downloaded file corresponds to the uploaded one


## Human Resource/Time Estimation:

Number of sprints required: 1

Number of developers required: 2
