
@metadata @upload
Feature: 140 Download Metadata
  As a user, I can download metadata from the system

  Scenario: Downloading metadata from the system

    Given we have the state "metadata has been loaded into the system"

    When metadata of dataset "DS_A" is downloaded from the system
    Then the response status code is "200"
    And the downloaded spreadsheet should match the expected for dataset "DS_A"
