@browse @metadata @artifacts
Feature: 27 Dataset Details
  As a user, I can show a dataset detail view

  Scenario: View details of dataset 1
    When I request the details of "DS_1" dataset
    Then the response status code is "200"
    And I get the details of "DS_1" dataset

  Scenario: View details of dataset B
    When I request the details of "DS_B" dataset
    Then the response status code is "200"
    And I get the details of "DS_B" dataset

    When I request an associated sample resource
    Then the response status code is "200"
    And I get a sample resource

  Scenario: Viewing a non-existing dataset
    When I request the details of "non-existing" dataset
    Then the response status code is "404"
