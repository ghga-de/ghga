@unhappy @auth @users
Feature: 302 TOTP Reset After Deactivation
  A user who was deactivated due to failed TOTP login can log in again after reactivation.

  Scenario: Cleaning the session
    Given the session store is empty
    And the user "Dr. John Doe" is logged out
    And the user "Data Steward" is logged out

  Scenario: User fails TOTP verification and gets deactivated
    Given we have the state "user registration is completed"
    And I am logged in as "Dr. John Doe"

    When "Dr. John Doe" attempts TOTP verification with wrong codes
    And "Dr. John Doe" tries to log in
    Then the response status code is "401"
    And the response error message is "User account is disabled"

  Scenario: The data steward reactivates the user account
    Given I am logged in as "Data Steward"
    And I am authenticated as "Data Steward"
    Then "Data Steward" changes the status of "Dr. John Doe" to "active"

  Scenario: User successfully authenticates after reactivation
    Given the session store is empty
    And I am logged in as "Dr. John Doe"
    And I am authenticated as "Dr. John Doe"
    When "Dr. John Doe" retrieves their user data
    Then the expected user data of "Dr. John Doe" is returned
