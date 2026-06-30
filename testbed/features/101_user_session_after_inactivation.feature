@unhappy @auth @users
Feature: 301 User Account Inactivation
  User session must be inactivated immediately after account inactivation.

  Scenario: The user is logged in and authenticated
    Given we have the state "user registration is completed"
    And I am logged in as "Dr. John Doe"
    And I am authenticated as "Dr. John Doe"

  Scenario: The data steward inactivates the user account
    Given I am logged in as "Data Steward"
    And I am authenticated as "Data Steward"
    Then "Data Steward" changes the status of "Dr. John Doe" to "inactive"

  @xfail
  Scenario: Inactive user attempts to access data with a cached session
    When "Dr. John Doe" retrieves their user data
    Then the response status code is "401"

  Scenario: Inactive user attempts to log in
    Given the status of "Dr. John Doe" is "inactive"
    When "Dr. John Doe" tries to log in
    Then the response status code is "401"
    And the response error message is "User account is disabled"

  Scenario: Restoring the user account
    Given the status of "Dr. John Doe" is "inactive"
    Then "Data Steward" changes the status of "Dr. John Doe" to "active"
    When "Dr. John Doe" retrieves their user data
    Then the expected user data of "Dr. John Doe" is returned
