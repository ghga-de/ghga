# Up-/Download Client & Production POC (Star-Nosed Mole)

## Scope:
A scope definition can be found here: https://wiki.verbis.dkfz.de/x/fAFzCQ

## User Journeys

This epic covers the following user journeys:

### Data Upload:
![Data Upload](./images/data_upload.png)

A Data Submitter specifies the file ID, the URL to the Upload Contoller API, and the file path on the local file system using the CLI interface of the client (1.0). Internally, the CLI client translates the user-defined data into a request to the Upload Contoller API to obtain a pre-signed post URL (1.1). The client reads multiple parts from the source file in parallel (1.2) and uploads them as a stream using the pre-signed URL (1.3). Once the upload has been completed the client sends a confirmation to the Upload Controller API (1.4).


### Data Download:
![Data Download](./images/data_download.jpg)

A Data Requester Specifies the file ID,the URL to the DRS3 API,and the anticipated destination on the local file system using the CLI interface of the client (1.0).Internally,the CLI client translates the user-defined data Into a request to the DRS3 API in order to get a pre-signed download URL (1.1). Typically, the requested file is not already in the outbox. Thusthe API Instructs the CLI client to retry the request after a specified time again. The client waits the specified time and then repeats the request. This is repeated until the DRS3 API responds with the desired pre signed URL (1.2). The client fetches the file's bytes using the pre signed URL (1.3) and saves them to the local file system (1.4).


## CLI:

### Upload CLI:
```
ghga-cli upload-by-id \
    --api_url <url_to_upload_contoller> \
    --file-id <file_id> \
    --file_path <file_path>
```


### Download CLI:
```
ghga-cli download-by-id \
    --api_url <url_to_drs3> \
    --file-id <file_id> \
    --output_dir <output_dir>
```

## Additional Implementation Details:

- [Typer](https://typer.tiangolo.com/) can be used to implement the CLI interface.
- Ideally, avoid piping file bytes through python directly as this will slow down the upload/download significantly. Wrappers around C-based tools such as [pycurl](http://pycurl.io/docs/latest/) should be preferred.
- The installation should make as little assumptions of the execution environment as possible to allow its usage on a large variety of compute infrastructures:
    - The package should have minimal dependencies.
    - The existing dependencies should allow maximal flexibility when it comes to versions.
    - The package should be cross-platform compatible (Linux, Windows, MacOS).
- The package should be installable via PyPI.
- Name of the package is up for debate.

## Benchmarking
This epic not only contains implementation work but the produced solution is also benchmarked against a production s3 system.

### Benchmarking Senario:
- upload and download large file > 200 GB
- backend: Ceph S3 in Tübingen and(/or) IMB COS at DKFZ, GHGA file services may be deployed to an arbritrary de.NBI Cloud location
- client: outside of backend network (e.g. private computer, or VM in different location), should have reasonably fast internet connection

### Benchmarking Criteria:
- throughput/speed: duration of the up- and download process, average transfer rate
- reliability: occurrence of sporadic errors/unavailabilities when repeated multiple times
- (optional) scalability: is the experience deteriorating when uploading multiple large files (from multiple clients) in parallel?


## Human Resource/Time Estimation:

Number of sprints required: 2

Number of developers required: 1.5 (=1 Developer + 0.5 DevOps)
