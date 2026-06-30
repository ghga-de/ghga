@files @ingest @unhappy
Feature: 201 Unhappy File Ingest
  As a data steward, I want to receive meaningful messages when file ingestion fails

  Scenario: Attempt to ingest existing file again
    Given we have the state "files have been uploaded and ingested"
    And all the file metadata is stored in the internal file registry
    When an existing file is attempted to be ingested again
    Then I get an error message that the metadata has already been processed

  Scenario Outline: Attempt to ingest files with invalid submission information

    When the file metadata is ingested "<info_case>" submission information
    Then the command line message is "<expected_message>"

    Examples:
      | info_case    | expected_message                                      |
      | without      | Missing option '--submission-id'                      |
      | with invalid | The submission with the following ID does not exist   |
