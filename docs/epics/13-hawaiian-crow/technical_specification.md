# S3 File I/O Benchmarking using hexkit and CLI (Hawaiian Crow)
**Epic Type:** Exploratory Epic

## Scope
A scope definition can be found here: https://wiki.verbis.dkfz.de/x/sICcCw

## Principle Components of Exploration:
This epic covers benchmarking performance and reliability of S3 upload/download using hexkit and CLI functionality.

## Material and Resources:

### Test files:

Test files consist of four categories:

- Sub multipart: < 5 MiB
- Small file: ~ 10 GiB
- Medium file: ~ 50 GiB
- Big file: ~ 150 GiB (not bigger than 160 GiB)

Content in the test files consists of sequence data in FASTA format.

### Benchmarking Setup:

Benchmarking will be performed on the Ceph Storage in Tübingen and the IBM COS Storage in Heidelberg.
For Benchmarking, a dedicated VM in the de.NBI Cloud in the respective other location will be set up.
Thus Tübingen will be tested from Heidelberg and vice versa.

### Benchmarking Script:

Create a benchmarking scipt based on the S3 provider implementation in hexkit (https://github.com/ghga-de/hexkit/blob/main/hexkit/providers/s3/provider.py) and file operation functions from the CLI (https://github.com/ghga-de/ghga-connector/blob/main/ghga_connector/core/file_operations.py).

### Benchmarking Goals:

- How fast are the downloads/uploads? Determine average duration and transfer rate
- Establish how reliable the upload/download processes are: Do sporadic errors/unavailabilities occurr?
For reliability testing, run a continuous upload cycle (~2 days).
- (Optional) Determine if content structure has influence on the up-/download performance

## Additional Details:
- IBM COS Documentation: https://cloud.ibm.com/docs/cloud-object-storage
- IBM COS expert in Heidelberg: Koray
- Ceph Documentation: https://docs.ceph.com/en/quincy/
- Ceph Storage in Tübingen deployed by Sardina Systems (info@sardinasystems.com)
- Ceph Storage & de.NBI expert in Tübingen: Moritz

## Human Resource/Time Estimation:

Number of sprints required: 1

Number of developers required: 1
