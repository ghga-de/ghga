@download @auth
Feature: 30 User Registration
  Users can register themselves and then login.

  Scenario: Reqistration as a new user

    Given the user "Dr. John Doe" is not yet registered
    When the user "Dr. John Doe" retrieves the own user data
    Then the response status code is "404"

    When the user "Dr. John Doe" tries to register
    Then the response status code is "201"
    And the user data of "Dr. John Doe" is returned

    When the user "Dr. John Doe" retrieves the own user data
    Then the response status code is "200"
    And the user data of "Dr. John Doe" is returned

  Scenario: The data steward should be pre-registered

    When the user "Data Steward" retrieves the own user data
    Then the response status code is "200"
    And the user data of "Data Steward" is returned
