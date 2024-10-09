@download @auth
Feature: 300 User Registration
  Users can register themselves and then authenticate.

  "Logged in" = authenticated with 1st factor only (OIDC).
  "Authenticated" = fully authenticated with 2nd factor (TOTP).

  Scenario: Cleaning the session and TOTP cache
    Given the session store is empty
    And the TOTP token store is empty
    And no notification has been sent yet
    And the state of "Data Steward" IVA is "Unverified"

  Scenario: Attempt to access user data without login
    Given the user "Dr. John Doe" is not yet registered
    When "Dr. John Doe" retrieves their user data
    Then the response status code is "403"

  Scenario: Attempt to access user data when not fully authenticated
    Given the user "Dr. John Doe" is not yet registered
    And I am logged in as "Dr. John Doe"
    When "Dr. John Doe" retrieves their user data
    Then the response status code is "403"

  Scenario: Successful registration of a new user
    Given I am logged in as "Dr. John Doe"
    When "Dr. John Doe" registers as a new user
    Then the response status code is "201"
    And the expected user data of "Dr. John Doe" is returned

  Scenario: Access user data after authentication
    Given I am logged in as "Dr. John Doe"
    And I am registered as "Dr. John Doe"
    And I am authenticated as "Dr. John Doe"
    When "Dr. John Doe" retrieves their user data
    Then the expected user data of "Dr. John Doe" is returned

  Scenario: The user has a new email address
    Given the user "Dr. John Doe" is logged out
    And "Dr. John Doe" has a new email address
    And I am logged in as "Dr. John Doe"
    When I retrieve a new TOTP token as "Dr. John Doe"
    Then the session state is "NeedsReRegistration"
    And I get the error "Cannot create TOTP token at this point"

  Scenario: The user re-registers with the old email address
    When "Dr. John Doe" re-registers with the old email
    Then the response status code is "422"

  Scenario: The user re-registers with the new email address
    When "Dr. John Doe" re-registers with the new email
    Then the response status code is "204"
    And "Account Details Changed" was sent to "Dr. John Doe"

  Scenario: Trying to change the title without authentication
    When "Dr. John Doe" changes the title to "Prof."
    Then the response status code is "403"

  Scenario: The user creates a new TOTP token
    Given I am logged in as "Dr. John Doe"
    When I retrieve a new TOTP token as "Dr. John Doe"
    Then the session state is "HasTotpToken"

  Scenario: Changing the title after authentication
    Given I am authenticated as "Dr. John Doe"
    When "Dr. John Doe" changes the title to "Prof."
    Then the response status code is "204"
    And "Second Factor Recreated" was sent to "Dr. John Doe (new email)"

  Scenario: Access user data again after changes
    Given I am logged in as "Prof. John Doe"
    And I am authenticated as "Prof. John Doe"
    When "Prof. John Doe" retrieves their user data
    Then the expected user data of "Prof. John Doe" is returned

  Scenario: Changing the title back again
    Given I am authenticated as "Prof. John Doe"
    When "Prof. John Doe" changes the title to "Dr."
    Then the response status code is "204"

  Scenario: The user has the old email address again
    Given the user "Dr. John Doe" is logged out
    And "Dr. John Doe" has the old email address
    And I am logged in as "Dr. John Doe"
    When "Dr. John Doe" re-registers with the old email
    Then the response status code is "204"
    And "Account Details Changed" was sent to "Dr. John Doe (new email)"

  Scenario: The user creates another TOTP token
    Given I am logged in as "Dr. John Doe"
    When I retrieve a new TOTP token as "Dr. John Doe"
    Then the session state is "HasTotpToken"

  Scenario: Access user data again after reset
    Given I am logged in as "Dr. John Doe"
    And I am authenticated as "Dr. John Doe"
    When "Dr. John Doe" retrieves their user data
    Then the expected user data of "Dr. John Doe" is returned
    And "Second Factor Recreated" was sent to "Dr. John Doe"

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
    And the expected user data of "Data Steward" is returned

  Scenario: The data steward cannot access user data
    When "Data Steward" retrieves the user data of "Dr. John Doe"
    Then the response status code is "403"
    And the response error message is "Not authorized to request user"

  Scenario: The data steward has a verified IVA
    Given the user "Data Steward" is logged out
    And the state of "Data Steward" IVA is "Verified"
    And I am logged in as "Data Steward"
    And I am authenticated as "Data Steward"
    When "Data Steward" retrieves the user data of "Dr. John Doe"
    Then the response status code is "200"

  Scenario: Finishing the registration
    Then set the state to "user registration is completed"
