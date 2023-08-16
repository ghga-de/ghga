@browse @metadata @artifacts
Feature: 27 Dataset Details
  As a user, I can show a dataset detail view

  # TBD: more scenarios

  Scenario: Viewing the details of a dataset
    When I request the complete-A dataset resource
    Then the response status code is "200"
    And the complete-A dataset resource is returned

  Scenario: Viewing a non-existing dataset
    When I request a non-existing dataset resource
    Then the response status code is "404"
