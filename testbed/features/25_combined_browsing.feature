@browse @metadata @mass
Feature: 25 Combined Browsing of Datasets
  As a user, I can use a combination of searching, filtering and pagination

  Scenario: Searching datasets with combined features
    When I search "STUDY_A" and request page "2" with page size "2"
    Then the response status code is "200"
    And the expected hit count is "4"
    And I receive "2" items

  Scenario: Searching in filtered datasets
    When I filter dataset with type "A Type"
    Then the response status code is "200"
    And the expected hit count is "4"

    When I search "STUDY_B" in datasets with type "A Type"
    Then the response status code is "200"
    And the expected hit count is "2"
    And I receive "2" items
