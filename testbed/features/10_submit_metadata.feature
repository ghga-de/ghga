@metadata @submission
Feature: 10 Submit Metadata
  As a data steward, I can submit research metadata into local submission registry

  Scenario: Submitting metadata

    Given we start on a clean slate
    And we have a valid research metadata JSON file
    And we have a valid metadata config YAML file

    When metadata is submitted to the submission registry
    Then a submission JSON exists in the local submission registry

    Then set the state to "metadata submission is completed"
