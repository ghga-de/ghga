# File Encryption & Decryption Services (Hooded Crow)
**Epic Type:** Implementation Epic


## Scope:
A scope definition can be found here: https://wiki.verbis.dkfz.de/x/TgA5D
## User Journeys

Building on the [*16 - Cuban Crow*](../16-cuban-crow/technical_specification.md) epic, this implementation epic aims to develop the functionality explored in the prototype script into fully fledged services to deal with encryption and decryption functionality using Crypt4GH along both the download and upload path.
For this purpose, work is separated into two general user journeys, one for upload and one for download.

### 1. Implement *Interrogation Room* and  *Encryption Key Store* services for file upload

The diagram below shows the general flow between already existing services and the position of the new services in this network of interactions.

```mermaid
graph TD
    cli[CLI] -- 1. upload --> inbox[Inbox]
    cli -- 2. confirm upload --> ulc[Upload Controller]
    ulc -. 3. successful upload .-> ir[Interrogation Room]
    ir -. 4. request file parts .-> inbox
    inbox -. 5. receive file parts .-> ir
    ir -- 6. send first part --> eks[Encryption Key Store]
    eks -. 7. store encryption/decryption secret, secret id .-> vault[HashiCorp Vault]
    eks -- 8. return secret, secret id, file content offset --> ir
    ir -- 9. decrypt file, compute and validate checksums --> ir
    ir -. 10a. send success  message .-> ifr[Internal File Registry]
    ir -. 10b. send failure message .-> ulc
```
This user journey comprises a set of goals for both the *Interrogation Room* and *Encryption Key Store*.
The user should be able to upload a file encrypted with the crypt4gh tool using his private and the current GHGA public key, which will further be processed by the two services.
In addition a SHA256 checksum of the unencrypted file needs to be provided by either the user or computed by the CLI which is used to verify intergrity of the confirmed upload (will be done in an upcoming epic).

> *Interrogation Room*
> 1. The first file part of the confirmed uploaded file ist requested and forwarded to the *Encryption Key Store* to process information contained in the Crypt4GH envelope.
> 2. The information returned is used to produce SHA256 checksums for all encrypted file parts corresponding to actual file content, i.e. excluding the envelope.
File part size corresponds to the part size used in the multipart upload.
In addition, the file content is decrypted in chunks in memory and fed into a SHA256 checksum algorithm to produce a checksum for the entire file content.
> 3. This checksum is compared for equality with the user provided checksum.
In case of a mismatch an event is emitted to be processed by the *Upload Controller* to notify the user of the upload failure.
Else an event is emitted to be processed by the *Internal File Registry* and the encrypted file content, i.e. without envelope, is moved to permanent storage.
Defining the message formats for those events is part of an upcoming epic.

> *Encryption Key Store*
> 1. Retrieve the GHGA secret key from HashiCorp Vault.
> 2. Crypt4GH functionality is used to find the envelope and extract the file encryption/decryption secret contained within using the GHGA secret key.
Furthermore, the file content offset is obtained.
> 3. A SHA256 sum over the file encryption/decryption key is generated as its ID and both the key and ID are saved in HashiCorp Vault.
> 4. The key, its ID and the file content offset are returned as response to the *Interrogation Room*.

### 2. Implement *Encryption Key Store* service for file download
The diagram below shows the general flow between already existing services and the position of the new service in this network of interactions.

```mermaid
graph TD
    cli[CLI] -- 1. request download --> dlc[Download Controller]
    dlc -. 2. stage file to outbox, if not present .-> ifr[Internal File Registry]
    ifr -- 3. multipart copy, validate checksums --> outbox[Outbox]
    ifr -. 4. ready for download .-> dlc
    dlc -- 5. request envelope --> eks[Encryption Key Store]
    eks -. 6. request ghga secret, file encryption/decryption secret .-> vault[HashiCorp Vault]
    vault -. 7.return ghga and file secret .-> eks
    eks -- 8. prepare personalized envelope --> eks
    eks -- 9. deliver envelope --> dlc
    dlc -- 10. generate pre-signed URL for combined envelope + file content --> dlc
    dlc -- 11. return pre-signed URL --> cli
    cli -- 12. download --> dlc
    dlc -- 13. request file parts --> outbox
    outbox -- 14. deliver file parts --> dlc
    dlc -- 15. deliver file parts - combined file --> cli
```
Following implementation goals for the *Encryption Key Store* shall be achieved in the context of this journey:
> 1. The *Encryption Key Store* receives a file ID for which a personalized envelope shall be generated for a given user's public key.
> 2. The GHGA secret key and the file encryption/decryption key for the given file id is retrieved.
> 3. A personalized envelope is constructed based on those three keys and returned to the download controller.

## User Journeys that are not part of this Epic:

Defining message formats for events at the boundaries of the *Interrogation Room* will be part of a follow-up epic.
Adjusting and integrating existing services will also be handled in that same epic and not in *Hooded Crow*.

## API Definitions:

### RESTful/Synchronous:
[Encryption Key Store REST API](./api_definitions/rest/encryption_key_store.yml) - [Swagger UI](https://editor.swagger.io/?url=https://raw.githubusercontent.com/ghga-de/epic-docs/main/18-hooded-crow/api_definitions/rest/encryption_key_store.yml)

## Additional Implementation Details:

Some tasks at the boundaries need to be dealt with directly during implementation of this epic.
Specific details on user public key storage and retrieval should go here, as well as secret ID storage and retrieval based on file ID.

## Human Resource/Time Estimation:

Number of sprints required: 2

Number of developers required: 2
