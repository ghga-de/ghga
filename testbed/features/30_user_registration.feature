@download @auth
Feature: 30 User Registration
  Users can register themselves and then authenticate.

  "Logged in" = authenticated with 1st factor only (OIDC).
  "Authenticated" = fully authenticated with 2nd factor (TOTP).

  Scenario: Cleaning the session and TOTP cache
    Given the session store is empty
    And the TOTP token store is empty

  Scenario: Attempt to access user data without login
    Given the user "Dr. John Doe" is not yet registered
    When "Dr. John Doe" retrieves their user data
    Then the response status code is "403"

  Scenario: Attempt to access user data when not fully authenticated
    Given the user "Dr. John Doe" is not yet registered
    And I am logged in as "Dr. John Doe"
    When "Dr. John Doe" retrieves their user data
    Then the response status code is "403 (with API gateway) or 404 (without)"

  Scenario: Successful registration of a new user
    Given I am logged in as "Dr. John Doe"
    When "Dr. John Doe" registers as a new user
    Then the response status code is "201"
    And the user data of "Dr. John Doe" is returned

  Scenario: Access user data after authentication
    Given I am logged in as "Dr. John Doe"
    And I am registered as "Dr. John Doe"
    And I am authenticated as "Dr. John Doe"
    When "Dr. John Doe" retrieves their user data
    Then the user data of "Dr. John Doe" is returned

  Scenario: The data steward lost the TOTP token
    Given I lost my TOTP token as "Data Steward"
    And I am logged in as "Data Steward"
    When I retrieve a new TOTP token as "Data Steward"
    Then the new TOTP token for "Data Steward" is validated

  Scenario: The data steward should be pre-registered
    Given I am logged in as "Data Steward"
    And I am authenticated as "Data Steward"
    When "Data Steward" retrieves their user data
    Then the response status code is "200"
    And the user data of "Data Steward" is returned

  Scenario: Finishing the registration
    Then set the state to "user registration is completed"
