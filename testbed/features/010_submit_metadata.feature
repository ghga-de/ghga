@metadata @submission
Feature: 10 Submit Metadata
  As a data steward, I can submit research metadata
  into the local submission store

  Scenario: Starting the metadata submission
    Given we start on a clean slate
    And we have a valid metadata config YAML file
    Then no submission JSON files exist in the local submission store

  Scenario: Migrating a submission store from before study PIDs
    Given the submission store holds the legacy submission of study X
    When the accession store is migrated
    Then the accession store keeps the flat accessions as legacy ones
    And one submission JSON file exists in the local submission store

  Scenario: Submitting metadata
    Given we have valid research metadata JSON files
    When the metadata is submitted to the submission store
    Then three submission JSON files exist in the local submission store

  Scenario: Amending a submission with study PIDs is refused
    When the submission is amended with the same metadata
    Then the amendment is refused, since the submission has study PIDs
    And three submission JSON files exist in the local submission store
    And the accessions of the submission are unchanged

  Scenario: Amending the legacy submission with an added file
    When the legacy submission of study X is amended with an added file
    Then the amendment is applied
    And the legacy submission keeps its accessions
    And the added file has a flat accession
    And three submission JSON files exist in the local submission store

  Scenario: Finishing the metadata submission
    Then set the state to "metadata submission is completed"
