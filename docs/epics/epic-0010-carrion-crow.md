# File Tech Stack Exploration (Carrion Crow)
**Epic Type:** Exploratory Epic

## Scope:
A scope definition can be found here: https://wiki.verbis.dkfz.de/x/YQH9Cg

## Components of Exploration:
This epic covers principle technologies that might be used in the context of file handling


### Select Test Files

For the whole epic, select 4 distinct test files. They shall have the sizes:

- Small file: Between 10 and 100 MiB
- Medium file: Between 1 and 10 GiB
- Big file: ~ 50 GiB
- Maximum possible file ~ 150 GiB (not bigger than 160 GiB)

### Crypt4GH

Benchmark the python and rust implementation of crypt4GH in the de.NBI cloud, using all four file sizes. Benchmark criteria are:

- How long does it take for each implementation/file size?
- Encryption speed (bytes per second)?
- Is multithreading possible?
- Capture Memory and CPU footprint
- Watch for problems (System freezes, etc.)

Answer the following questions:

- Find out, how to separate the encrypted contend from the envelope, so the encrypted contend can be reused.
- Does crypt4GH already come with checksum validation?
- Does the encrypting party need to provide its own public key and does this need to be checked by the receiving/decrypting party? (Reference the crypt4GH concept and concrete implementation.)


### Checksum validation

Compare the following widely used checksum algorithms - they are the ones also used by Amazon S3:

- MD5
- CRC-32
- CRC-32C
- SHA-1
- SHA-256

List advantages and disadvantages of each algorythm. Benchmark in the de.NBI cloud, how long checksum calculations for the same file take with each algorithm. Use all four file sizes.

Find out, which of these checksum algorithms are also supported by the Ceph and IBM COS S3 API.

### FastQC

FastQC has been omitted from this epic and moved to a future epic (no specifics yet).

### Volume/ Hardware Level encryption

Volume/ Hardware Level encryption has been omitted from this epic and moved to a future epic (no specifics yet).

## Material and Resources:

### Realistic Sample files:
Take samples from the Genome in a bottle (GIAB) project: https://ftp-trace.ncbi.nih.gov/ReferenceSamples/giab/data/
Another source for publicly available genome files would be the 1000 Genomes project: http://ftp.1000genomes.ebi.ac.uk/

### crypt4GH:
- crypt4GH Documentation: http://samtools.github.io/hts-specs/crypt4gh.pdf
- crypt4GH python utility: https://crypt4gh.readthedocs.io/en/latest/
- crypt4GH rust utility: https://docs.rs/crypt4gh/latest/crypt4gh/


## Human Resource/Time Estimation:

Number of sprints required: 2

Number of developers required: 1.5
