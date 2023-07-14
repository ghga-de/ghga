@metadata @ingest
Feature: 13 Ingest File Metadata
  As a data steward, I can output metadata files to the file ingest service

  Scenario: Ingesting file metadata

    Given we have the state "Files uploaded successfully"

    When file metadata is ingested
    Then we have the file accessions
    And file metadata exist in the service
    And files exist in permanent bucket
    And set the state to "File metadata ingested successfully"
