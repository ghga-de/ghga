@browse @metadata @files
Feature: 280 Dataset File Information
  As a user, I can view available metadata about files registered

  Background:
    Given we have the state "all available datasets"
    And we have the state "all file information"

  Scenario: View details of all files in the dataset A
    When I request the details of all files in "DS_A" dataset
    Then the response status code is "200"
    And I get the details of all files in "DS_A" dataset

  Scenario: View details of all files in the dataset B
    When I request the details of all files in "DS_B" dataset
    Then the response status code is "200"
    And I get the details of all files in "DS_B" dataset

  Scenario: View details of a non existing dataset
    When I request the details of all files in "non-existing" dataset
    Then the response status code is "404"

  Scenario: View details of a single file
    When I request the details of "single" file
    Then the response status code is "200"
    And I get the details of the file correctly

  Scenario: View details of a non existing file
    When I request the details of "non-existing" file
    Then the response status code is "404"
