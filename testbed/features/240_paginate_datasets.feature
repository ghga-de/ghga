@browse @metadata @mass
Feature: 24 Paginate Datasets
  As a user, I can use pagination when browsing the public datasets

  Background:
    Given we have the state "metadata has been loaded into the system"

  Scenario: Requesting results on subsequent pages
    When I request page "2" with a page size of "1"
    Then the response status code is "200"
    And I get "1" out of "2" search results

  Scenario: Requesting results on invalid page
    When I request page "1" with a page size of "5"
    Then the response status code is "200"
    And I get "2" out of "2" search results
