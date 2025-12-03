@files @ingest @unhappy
Feature: 121 Ingest Existing Files Again
  Same file metadata can not be ingested again.

  Scenario: Attempt to ingest existing file again
    Given we have the state "files have been uploaded and ingested"
    And all the file metadata is stored in the internal file registry
    When an existing file is attempted to be ingested again
    Then I get an error message that the metadata has already been processed
