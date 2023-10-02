@browse @metadata @mass
Feature: 22 Search Datasets
  As a user, I can filter the public datasets

  Background:
    Given we have the state "metadata has been loaded into the system"

  Scenario: Verify searching with invalid query
    When I search documents with invalid query format
    Then the response status code is "422"

  Scenario: Search datasests without any keyword
    When I search datasets without any keyword
    Then the response status code is "200"
    And I get all the existing datasets

  Scenario: Search datasets with a word not found in
    When I search datasets with the "hotel" query
    Then the response status code is "200"
    And the expected hit count is "0"

  Scenario: Search datasets with a common keyword
    When I search datasets with the "dataset" query
    Then the response status code is "200"
    And the expected hit count is "6"

  Scenario: Search datasets with study alias
    When I search datasets with the "STUDY_A" query
    Then the response status code is "200"
    And the expected hit count is "4"
    And I get the expected results from study search

  Scenario: Search datasets by keyword matching
    When I search datasets with the "An interesting dataset C" query
    Then the response status code is "200"
    And the expected hit count is "6"

  Scenario: Search datasets with exact description
    When I search datasets with the ""An interesting dataset C"" query
    Then the response status code is "200"
    And the expected hit count is "1"
    And I get the expected results from description search
