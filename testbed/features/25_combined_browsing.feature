@browse @metadata @mass
Feature: 25 Combined Browsing of Datasets
  As a user, I can use a combination of searching, filtering and pagination

  Scenario: Searching datasets combined and requesting first page
    When I search "STUDY_A" and request page "1" with page size "2"
    Then the response status code is "200"
    And the expected hit count is "1"
    And I receive "1" items

  Scenario: Searching datasets combined and requesting empty page
    When I search "STUDY_A" and request page "2" with page size "2"
    Then the response status code is "200"
    And the expected hit count is "1"
    And I receive "0" items

  Scenario: Filtering datasets by type
    When I filter dataset with type "A Type"
    Then the response status code is "200"
    And the expected hit count is "1"

  Scenario: Searching in filtered datasets
    When I search "STUDY_B" in datasets with type "A Type"
    Then the response status code is "200"
    And the expected hit count is "0"
    And I receive "0" items
