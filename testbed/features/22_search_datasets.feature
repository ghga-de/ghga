
@browse @metadata
Feature: 22 Search Datasets
  As a user, I can filter the public datasets

  Background:
    Given we have the state "metadata has been loaded into the system"
    And the database collection is prepared for searching

  Scenario: Verify searching with invalid query
    When I search documents with invalid query format
    Then the response status code is "422"

  Scenario: Search datasets with a word not found in
    When I search datasets with the "hotel" query
    Then the response status code is "200"
    And the expected hit count is "0"

  Scenario: Search datasets with a common keyword
    When I search datasets with the "dataset" query
    Then the response status code is "200"
    And the expected hit count is "2"

  Scenario: Search datasets with file format
    When I search datasets with the "vcf" query
    Then the response status code is "200"
    And the expected hit count is "2"

  Scenario: Search datasets with study alias
    When I search datasets with the "STUDY_A" query
    Then the response status code is "200"
    And the expected hit count is "1"
    And I get the expected results from study search

  Scenario: Search datasets by keyword matching
    When I search datasets with the "An interesting dataset B" query
    Then the response status code is "200"
    And the expected hit count is "2"

  Scenario: Search datasets with exact description
    When I search datasets with the ""An interesting dataset B"" query
    Then the response status code is "200"
    And the expected hit count is "1"
    And I get the expected results from description search
