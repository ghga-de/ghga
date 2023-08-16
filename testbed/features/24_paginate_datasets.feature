@browse @metadata @mass
Feature: 24 Paginate Datasets
  As a user, I can use pagination when browsing the public datasets

  Background:
    Given we have the state "metadata has been loaded into the system"

  Scenario: Requesting results on subsequent pages
    When I request page "3" with a page size of "2"
    Then the response status code is "200"
    And the expected hit count is "6"
    And I receive "2" items

  Scenario: Requesting results on invalid page
    When I request page "3" with a page size of "3"
    Then the response status code is "200"
    And the expected hit count is "6"
    And I receive "0" items
