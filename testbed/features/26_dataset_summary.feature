@browse @metadata @artifacts
Feature: 26 Dataset Summary
  As a user, I can show a dataset summary view

  Scenario: View summary of dataset 3
    When I request the summary of "DS_3" dataset
    Then the response status code is "200"
    Then I get the summary of "DS_3" dataset

  Scenario: View summary of dataset A
    When I request the summary of "DS_A" dataset
    Then the response status code is "200"
    Then I get the summary of "DS_A" dataset

  Scenario: View summary of non-existing dataset
    When I request the summary of "non-existing" dataset
    Then the response status code is "404"
