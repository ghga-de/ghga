@upload @files
Feature: 12 Upload Files
  As a data steward, I can upload files to object storage

  Background:
    Given we have the state "metadata submission is completed"
    And no files have been uploaded yet
    And no file metadata exists

  Scenario: Uploading single file

    When a single file is uploaded
    Then the file metadata for the uploaded file exists
    And the uploaded file exists in the staging bucket

  Scenario: Batch uploading files

    When multiple files are uploaded as a batch
    Then the file metadata for each uploaded file exists
    And the uploaded files exist in the staging bucket

    Then set the state to "files have been uploaded"
