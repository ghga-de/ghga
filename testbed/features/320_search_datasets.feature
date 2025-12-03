@browse @metadata @mass
Feature: 22 Search Datasets
  As a user, I can filter the public datasets

  Background:
    Given we have the state "metadata has been loaded into the system"

  Scenario: Verify searching with an unknown class name
    When I search documents with an unknown class name
    Then the response status code is "422"

  Scenario: Search datasests without any keyword
    When I search datasets without any keyword
    Then the response status code is "200"
    And I get all the existing datasets

  Scenario: Search datasets with a word not found in
    When I search datasets with the "hotel" query
    Then the response status code is "200"
    And I get "0" search results

  Scenario: Search datasets with a common keyword
    When I search datasets with the "dataset" query
    Then the response status code is "200"
    And I get "2" search results

  Scenario: Search datasets with study alias
    When I search datasets with the "STUDY_A" query
    Then the response status code is "200"
    And I get only dataset "EGADATASET000A" as search result

  Scenario: Search datasets by keyword matching
    When I search datasets with the "An interesting dataset C" query
    Then the response status code is "200"
    And I get "2" search results

  Scenario: Search datasets with exact description
    When I search datasets with the ""An interesting dataset B"" query
    Then the response status code is "200"
    And I get only dataset "EGADATASET000B" as search result
