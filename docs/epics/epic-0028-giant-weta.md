# Batch Download for the CLI Client (Giant Weta)
**Epic Type:** Implementation Epic

**Attention: Please do not put any confidential content here.**

## Scope:

This Epic covers the following features to be implemented into the GHGA-Connector:

- Batch download of multiple files
- files will be downloaded in sequence, no parallelization across files

It does not include:
- Batch upload of multiple files

## Additional Implementation Details:

### Batch Download

The following information will be retrieved from a REST api call to the work package service.
For now, we want to have an explicit function that pulls the information from env variables which we can later swap for a function calling the WPS api:

- The list of files (file IDs) to be downloaded
- The file endings of those files
- The user’s identity (the internal user ID)
- The user’s public crypt4GH key to use
- The current GHGA public crypt4GH key to use

An additional check should be implemented to compare the retrieved users public key with the one provided by the WPS.

With the newly added file ending, we want to add the file ending to the file for the following structure:
`{file_id}.{file_extension}.c4gh`
Additionally, we want to distinguish between finished files and files in progress.
Therefore, all partial files will now be added the file ending `.part`.
This ending will be removed, once the download is completed.
If a download fails, its corresponding `.part` file will be deleted.
Also, if a `.part` file already exists upon starting a download, we just replace it.

At last, we will add a batch script, which will take the list of files to call the download function for each file.
Before that, at first each file will be called using the `GET /objects/{object_id}` endpoint.
This for one checks, if the file is actually availble for download and also triggers staging it in the `outbox` bucket.
The list will also be re-ordered according to the shortest wait time (Files that are already staged will be downloaded first).
This batch script will also check if files already exist in the provided download location.
For either one, the script will provide an output, explaining which files already exist in the outbox and which files won't be available to download.
The user is prompted to either skip those files or cancel the batch download.
This prompt can also be skipped by setting individual flags (e.g. `--skip-downloaded`, `--skip-unavailable`)


## Human Resource/Time Estimation:

Number of sprints required: 1

Number of developers required: 1
