@download @ars
Feature: 32 Access Request
  As a user, I can ask for access request to a given dataset.

  Scenario: Requesting access to a dataset

    Given we have the state "metadata has been loaded into the system"
    And the claims repository is empty
    And no access requests have been made yet
    And I am registered as "Dr. John Doe"

    Given I am logged in as "Dr. John Doe"
    And I am authenticated as "Dr. John Doe"

    When "Dr. John Doe" requests access to the test dataset "DS_A"
    Then the response status code is "201"
    And "Access Request Created" notification was sent to "Central Data Steward"
    And "Access Request Registered" notification was sent to "Dr. John Doe"

  Scenario: Viewing the pending access request

    Given I am logged in as "Data Steward"
    And I am authenticated as "Data Steward"

    When "Data Steward" fetches the list of access requests
    Then the response status code is "200"
    And there is one request for test dataset "DS_A" from "Dr. John Doe"
    And the status of the request from "Dr. John Doe" is "pending"

  Scenario: Granting access to the pending request

    When "Data Steward" allows the pending request from "Dr. John Doe"
    Then the response status code is "204"

  Scenario: Confirming the status of access request

    Given I am logged in as "Data Steward"
    And I am authenticated as "Data Steward"

    When "Data Steward" fetches the list of access requests
    Then the response status code is "200"
    And there is one request for test dataset "DS_A" from "Dr. John Doe"
    And the status of the request from "Dr. John Doe" is "allowed"
    And "Access Request Allowed" notification was sent to "Central Data Steward"
    And "Access Request Accepted" notification was sent to "Dr. John Doe"
    And set the state to "John Doe is allowed to download the test dataset"
