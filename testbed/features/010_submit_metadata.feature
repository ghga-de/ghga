@metadata @submission
Feature: 10 Submit Metadata
  As a data steward, I can submit research metadata
  into the local submission store

  Scenario: Starting the metadata submission
    Given we start on a clean slate
    And we have a valid metadata config YAML file
    Then no submission JSON files exist in the local submission store

  Scenario: Submitting metadata
    Given we have valid research metadata JSON files
    When the metadata is submitted to the submission store
    Then one submission JSON file exists in the local submission store

  Scenario: Finishing the metadata submission
    Then set the state to "metadata submission is completed"
