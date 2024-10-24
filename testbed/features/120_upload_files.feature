@upload @files
Feature: 12 Upload Files
  As a data steward, I can upload files to object storage

  Background:
    Given we have the state "metadata submission is completed"
    And the staging buckets are empty
    And no file metadata exists

  Scenario: Uploading files individually

    When the files of dataset "DS_A" are uploaded to "primary" storage individually
    Then the file metadata for each uploaded file exists
    And the uploaded files exist in the staging bucket of "primary" storage

  Scenario: Batch uploading files of dataset A

    Given no file encryption secrets exist in the vault
    When "all" files of dataset "DS_A" are uploaded to "primary" storage in batch
    Then the file metadata for each uploaded file exists
    And the uploaded files exist in the staging bucket of "primary" storage
    When the file metadata uploaded to "primary" storage is ingested
    Then the file metadata is stored in the internal file registry
    And the file encryption secret is saved in the vault
    And the ingested files exist in the permanent bucket of "primary" storage

  Scenario: Batch uploading TXT files of dataset B

    When "txt" files of dataset "DS_B" are uploaded to "primary" storage in batch
    Then the file metadata for each uploaded file exists
    And the uploaded files exist in the staging bucket of "primary" storage
    When the file metadata uploaded to "primary" storage is ingested
    Then the file metadata is stored in the internal file registry
    And the file encryption secret is saved in the vault
    And the ingested files exist in the permanent bucket of "primary" storage

  Scenario: Batch uploading FASTQ files of dataset B

    When "fastq" files of dataset "DS_B" are uploaded to "secondary" storage in batch
    Then the file metadata for each uploaded file exists
    And the uploaded files exist in the staging bucket of "secondary" storage
    When the file metadata uploaded to "secondary" storage is ingested
    Then the file metadata is stored in the internal file registry
    And the file encryption secret is saved in the vault
    And the ingested files exist in the permanent bucket of "secondary" storage

  Scenario: Finishing the file upload
    Then set the state to "files have been uploaded and ingested"
