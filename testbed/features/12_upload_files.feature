@upload @files
Feature: 12 Upload Files
  As a data steward, I can upload files to object storage

  Background:
    Given we have the state "metadata submission is completed"
    And the staging bucket is empty
    And no file metadata exists

  Scenario: Uploading files individually

    When the files for the minimal metadata are uploaded individually
    Then the file metadata for each uploaded file exists
    And the uploaded files exist in the staging bucket

    When the file metadata is ingested
    Then the file metadata is stored in the internal file registry
    And the ingested files exist in the permanent bucket

  Scenario: Batch uploading files

    When the files for the complete metadata are uploaded as a batch
    Then the file metadata for each uploaded file exists
    And the uploaded files exist in the staging bucket

    When the file metadata is ingested
    Then the file metadata is stored in the internal file registry
    And the ingested files exist in the permanent bucket

  Scenario: Finishing the file upload
    Then set the state to "files have been uploaded and ingested"
