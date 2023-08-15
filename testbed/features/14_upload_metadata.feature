
@metadata @upload
Feature: 14 Upload Metadata
  As a data steward, I can load metadata into the system

  Scenario: Loading metadata into the system

    Given we have the state "metadata transformation is completed"

    When metadata is loaded into the system
    Then the test datasets exist as embedded dataset in the database
    And the test datasets are known to the work package service

    Then set the state to "metadata has been loaded into the system"
