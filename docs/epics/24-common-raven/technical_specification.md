# Integration of all File Services - Download Stream (Common Raven)
**Epic Type:** Implementation Epic

The goal for this epic is to integrate all Backend File Services into the Testbed developed in [*19 - Pied Raven*](../19-pied-raven/technical_specification.md). This epic builds on [*23 - Thick-Billed Raven*](../23-thick-billed-raven/technical_specification.md) and aims to bring the Testbed to completion by including the complete file download path and changes required to make everything work according to the arch-concept.

## Scope:
A scope definition can be found here: https://wiki.verbis.dkfz.de/x/MIBSDQ

## User Journeys

This epic covers the following user journeys:

### Integration of File Services (Download Journey)

Produce a script to test the download path in the testbed and adapt the DCS and IFRS to allow for a fully functionioning download path.

### Re-Encryption

Add a new S3 bucket called "staging", with IRS write and IFRS read permissions. The IRS re-encrypts all files during checksum validation and the re-encrypted file is moved to the the staging bucket.

## Additional Implementation Details:

### IFRS
- The IFRS needs to consume the *NonStagedFileRequested* event, stage file to outbox and emit the *FileStagedForDownload* event afterwards
- Copy the encrypted, headless file from the staging bucket to the permanent storage after the "file_interrogation_success" event has been received

### DCS
- Adapt to request envelope from EKSS and serve the assembled file (envelope + encrypted file content) using custom download ranges

### EKSS
- When the IRS sends the first part, the EKSS now creates a new secret (using os.urandom(32) as per crypt4gh), and stores the new, instead of the old secret in vault. Both secrets are then sent back along with the ID generated for the new secret

### IRS
- During Interrogation: Re-Encrypt with the new key obtained from the EKSS, send file to staging bucket.
- Create Checksums for re-encrypted file instead of the original encrypted file. Part checksums now start directly from the encrypted file, as there is no header present.

### Testbed:

- Add a test script for the download path
    1. Run upload path script to populate permanent storage and IFRS state
    2. Request a file download through the ghga-connector
    3. Check for download staging events happening
    4. Verify the downloaded file corresponds to the uploaded one


## Human Resource/Time Estimation:

Number of sprints required: 2

Number of developers required: 2
