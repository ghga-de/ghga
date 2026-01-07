@dataportal @frontend
Feature: 401 Data Portal User Profile
  As a user, I can view and manage my GHGA account

    Background:

      Given the user has logged out of the Data Portal
      And the session store is empty

    Scenario: Regular user logs in to the Data Portal

      Given I am logged in as "Dr. John Doe"
      And I am logged in to the Data Portal as "Dr. John Doe"
      Then I get the homepage interface for "Dr. John Doe"

    Scenario: Data Steward logs in to the Data Portal

      Given I am logged in as "Data Steward"
      And I am logged in to the Data Portal as "Data Steward"
      Then I get the homepage interface for "Data Steward"

    Scenario Outline: User profile page
      Given we have the state "John Doe is allowed to download the test datasets"
      And all users have only a verified IVA
      And I am logged in as "<user>"
      And I am authenticated as "<user>"
      And I am logged in to the Data Portal as "<user>"

      When I navigate to the user account page
      Then I get the user profile page of "<user>"
      And I have an "SMS" contact address with state "Verified"
      And I have "<count>" granted access requests
      And I have no pending access requests

      Examples:
      | user           | count |
      | Dr. John Doe   | two   |
      | Data Steward   | no    |

    Scenario: Add new contact address

      Given all users have only a verified IVA
      And I am logged in as "Dr. John Doe"
      And I am authenticated as "Dr. John Doe"
      And I am logged in to the Data Portal as "Dr. John Doe"

      When I navigate to the user account page
      And I add a new "In Person" contact address with value "An example address"
      Then I have an "SMS" contact address with state "Verified"
      And I have an "In Person" contact address with state "Unverified"

      When I request verification for the "In Person" IVA
      Then I have an "In Person" contact address with state "CodeRequested"
      And set the state to "user has one IVA waiting for verification"

    Scenario: Data Steward sends code to the IVA

      Given we have the state "user has one IVA waiting for verification"
      And I am logged in as "Data Steward"
      And I am logged in to the Data Portal as "Data Steward"
      And I am authenticated as "Data Steward"

      When I load the admin page "IVA Manager"
      Then I list all the known IVAs in the system

      When I send the code to the IVA waiting for verification
      Then I filter one IVA with state "Code Transmitted"
      And remove the state "user has one IVA waiting for verification"
