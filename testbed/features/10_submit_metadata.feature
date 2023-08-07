@metadata @submission
Feature: 10 Submit Metadata
  As a data steward, I can submit research metadata into local submission registry

  Background:
    Given we start on a clean slate
    And we have a valid metadata config YAML file

  Scenario: Submitting minimal metadata

    Given we have a valid "minimal" research metadata JSON files
    When "minimal" metadata is submitted to the submission registry
    Then a submission JSON exists in the local submission registry

  Scenario: Submitting complete metadata

    Given we have a valid "complete" research metadata JSON files
    When "complete" metadata is submitted to the submission registry
    Then a submission JSON exists in the local submission registry
    And set the state to "metadata submission is completed"
