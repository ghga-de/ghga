@browse @metadata @artifacts
Feature: 20 Global Summary
  As a user, I can view the global summary statistics

  Background:
    Given we have the state "metadata has been loaded into the system"

  Scenario: View global summary
    When I get the global summary
    Then the response status code is "200"
    And the summary statistics is as expected
