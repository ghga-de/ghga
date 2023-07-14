@upload @files
Feature: 12 Upload Files
  As a data steward, I can upload files to object storage

  Scenario: Uploading files

    Given we have the state "Metadata submission is completed"

    When files are uploaded
    Then metadata for each file exist
    And set the state to "Files uploaded successfully"
