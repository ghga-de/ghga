
@download @metadata
Feature: 20 Examine Artifacts
  As a user, I can examine the available artifacts

  Background:
    Given we have the state "metadata has been loaded into the system"

  Scenario: Examining all artifact types
    When I request info on all available artifacts
    Then the response status code is "200"
    And I get the expected info on all the artifacts

  Scenario: Examining a single artifact type
    When I request info on the "embedded_public" artifact
    Then the response status code is "200"
    And I get the expected info on the "embedded_public" artifact

  Scenario: Examining a non-existing artifact type
    When I request info on the "non_existing" artifact
    Then the response status code is "404"

  Scenario: Viewing the details of a dataset
    When I request the complete-A dataset resource
    Then the response status code is "200"
    And the complete-A dataset resource is returned

  Scenario: Viewing a non-existing dataset
    When I request a non-existing dataset resource
    Then the response status code is "404"
