@auth @users
Feature: 311 User Management
  Data Stewards can retrieve, filter or update user accounts.

  Scenario: Cleaning the session
    Given the session store is empty
    And the user "Dr. John Doe" is logged out
    And the user "Prof. Mary Doe" has no TOTP token

  Scenario: Register a new test user
    Given the user "Prof. Mary Doe" is not yet registered
    And I am logged in as "Prof. Mary Doe"
    When "Prof. Mary Doe" registers as a new user
    Then the response status code is "201"
    And the expected user data of "Prof. Mary Doe" is returned

  Scenario: Regular user cannot access the list of users
    Given I am logged in as "Prof. Mary Doe"
    And I am authenticated as "Prof. Mary Doe"
    When "Prof. Mary Doe" retrieves the list of all users
    Then the response status code is "403"

  Scenario: Data steward accesses the list of users
    Given I am logged in as "Data Steward"
    And I am authenticated as "Data Steward"
    When "Data Steward" retrieves the list of all users
    Then the response status code is "200"
    And the expected item count in response is "3"
    And I get the details of all registered users

  Scenario: Data Steward deactivates a user
    Given I am logged in as "Data Steward"
    And I am authenticated as "Data Steward"
    Then "Data Steward" changes the status of "Prof. Mary Doe" to "inactive"
    When "Data Steward" retrieves the list of all users
    Then the response status code is "200"
    And the user status of "Prof. Mary Doe" is "inactive"

  Scenario: Data Steward deletes a user
    Given I am logged in as "Data Steward"
    And I am authenticated as "Data Steward"
    When "Data Steward" deletes the user "Prof. Mary Doe"

    When "Data Steward" retrieves the list of all users
    Then the response status code is "200"
    And the expected item count in response is "2"
    And I get the details of all registered users

  Scenario: Finishing the user management
    Then set the state to "user management is completed"
