@auth @users
Feature: 31 User Verification
  Users can verify their identity using independent verification addresses (IVAs).

  Scenario: User creates a phone IVA and receives a verification code

    Given we have the state "user registration is completed"
    And I am logged in as "Dr. John Doe"
    And I am authenticated as "Dr. John Doe"
    And all the IVAs of "Dr. John Doe" are deleted

    When "Dr. John Doe" adds "Phone" as an IVA
    And "Dr. John Doe" retrieves the list of "all" IVAs
    Then the expected item count is "1"
    And the state of IVA is "unverified"

    When "Dr. John Doe" requests verification for the "Phone" IVA
    Then the response status code is "204"

    Then "Dr. John Doe" receives an SMS for IVA verification code
    And "IVA Code Transmitted" email was sent to "Dr. John Doe"


  Scenario: User validates the phone IVA with the verification code

    When "Dr. John Doe" validates the "Phone" IVA with code
    Then the response status code is "204"

    When "Dr. John Doe" retrieves the list of "all" IVAs
    Then the expected item count is "1"
    And the state of IVA is "verified"


  Scenario: User creates a in person IVA and requests verification

    Given I am logged in as "Dr. John Doe"
    And I am authenticated as "Dr. John Doe"

    When "Dr. John Doe" adds "InPerson" as an IVA
    And "Dr. John Doe" retrieves the list of "unverified" IVAs
    Then the expected item count is "1"

    When "Dr. John Doe" requests verification for the "InPerson" IVA
    Then the response status code is "204"

    And "IVA Code Requested" email was sent to "Central Data Steward"
    And "IVA Verification Requested" email was sent to "Dr. John Doe"


  Scenario: Data Steward sends a verification code to the in person IVA

    Given I am logged in as "Data Steward"
    And I am authenticated as "Data Steward"

    When "Data Steward" creates a verification code for the "InPerson" IVA
    Then "Data Steward" sends the verification code to the "InPerson" IVA
    Then the response status code is "204"
    And "IVA Code Transmitted" email was sent to "Dr. John Doe"

  Scenario: User validates the in person IVA with verification code

    When "Dr. John Doe" validates the "InPerson" IVA with code
    Then the response status code is "204"

    When "Dr. John Doe" retrieves the list of "verified" IVAs
    Then the expected item count is "2"
