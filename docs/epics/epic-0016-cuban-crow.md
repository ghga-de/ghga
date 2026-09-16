# Prototyping Encryption & Decryption Workflow (Cuban Crow)
**Epic Type:** Exploratory Epic

This Epic aims to provide a script for prototyping all actions done by the future interrogation room and encrypted key store service layed out in the architecture concept for file validation and encryption (file upload as well as file download).

## Principle Components of Exploration:

The prototyping script will consist of two parts, upload and download. They should be run in sequence.

### Upload:

#### Interrogation room service functionality

- read first file part
- request (call function) decryption secret from encrypted key store (first file part attached)
- receive file encryption secret, secret ID and content offest from encrypted key store
- read file from disk part by part
    - compute checksum of individual encrypted file part, store in list 
    - decrypt file part
    - feed file part into checksum algorithm
- compare checksum of decrypted object with provided checksum
- save encrypted file without envelope
- publish (write to stdout) outcome of validation, list of checksums

#### Encrypted key store functionality

- receive first file part from interrogation room
- extract crypt4gh envelope
- decrypt envelope
- generate ID for encryption secret
- determine offset of the content
- return file encryption secret, secret ID and content offest to interrogation room

### Download:

In download, we currently do not use the interrogation room service.

#### Encrypted key store functionality

- receive request for user-specific envelope for a file
- request (read) file decryption secret with file secret ID
- request (read) current GHGA private key
- prepare envelope
- attach envelope to encrypted content
- decrypt file with crypt4gh tool and credentials
- calculate checksum of decrypted file, compare with provided checksum

### Optional functions

- Implement multiple users (at least two), where the script can be run with either user beeing the uploader and/or downloader.
- Implement multiple files which can be tested, provide all combinations of users and files as crypt4gh-encrypted files.
- Prepare functioning envelopes for all combinations of users and files to compare them with the produced envelopes at the end of the script.

## Material and Resources:

- File Validation and Encryption Concept for the workflow (https://github.com/ghga-de/arch_concepts/blob/main/file_validation_and_encryption.md)
- Crypt4GH Experiments for header separation (https://github.com/ghga-de/crypt4gh_experiments)

## Additional Implementation Details:

This Epic aims to only produce functions that will be executed within the interrogation room or the encrypted key store.
Communication between these services will only be simulated via function calls.
Communication with other services will be hardcoded.
Files that should be on object storage will be read from disc.
Public and private keys needed for encryption will either be hardcoded or read from disc.

## Human Resource/Time Estimation:

Number of sprints required: 1

Number of developers required: 2
