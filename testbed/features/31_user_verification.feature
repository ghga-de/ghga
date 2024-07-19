@download @auth
Feature: 31 User Verification
  Users can verify their identity using independent verification addresses (IVAs).

  Scenario: User creates an IVA and requests validation

    Given we have the state "user registration is completed"
    And I am logged in as "Dr. John Doe"
    And I am authenticated as "Dr. John Doe"
    And all the IVAs of "Dr. John Doe" are deleted

    When "Dr. John Doe" adds "Phone" as an IVA
    And "Dr. John Doe" retrieves the list of IVAs
    Then the expected item count is "1"
    And the state of IVA is "unverified"

    When "Dr. John Doe" requests verification for the IVA
    Then the response status code is "204"
    And "IVA Code Requested" was sent to "Central Data Steward"
    And "IVA Verification Requested" was sent to "Dr. John Doe"

  Scenario: Data Steward sends a verification code to the IVA

    Given I am logged in as "Data Steward"
    And I am authenticated as "Data Steward"

    When "Data Steward" creates a verification code for the IVA
    Then "Data Steward" sends the verification code to the IVA
    And "Data Steward" confirms the transmission of verification code
    Then the response status code is "204"
    And "IVA Code Transmitted" was sent to "Dr. John Doe"

  Scenario: User validates the IVA with verification code

    When "Dr. John Doe" validates the IVA with code
    Then the response status code is "204"

    When "Dr. John Doe" retrieves the list of IVAs
    Then the expected item count is "1"
    And the state of IVA is "verified"
    And "IVA Code Submitted" was sent to "Central Data Steward"
