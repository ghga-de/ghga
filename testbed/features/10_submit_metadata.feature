@metadata @submission
Feature: 10 Submit Metadata
  As a data steward, I can submit research metadata
  into the local submission store

  Scenario: Starting the metadata submission
    Given we have the state "health check is completed"
    And we start on a clean slate
    And we have a valid metadata config YAML file
    Then no submission JSON files exist in the local submission store

  Scenario: Submitting minimal metadata
    Given we have a valid "minimal" research metadata JSON files
    When "minimal" metadata is submitted to the submission store
    Then one submission JSON file exists in the local submission store

  Scenario: Submitting complete metadata
    Given we have a valid "complete" research metadata JSON files
    When "complete" metadata is submitted to the submission store
    Then two submission JSON files exist in the local submission store

  Scenario: Finishing the metadata submission
    Then set the state to "metadata submission is completed"
