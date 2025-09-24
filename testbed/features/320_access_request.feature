@download @ars
Feature: 320 Access Request
  As a user, I can ask for access request to a given dataset.

  Scenario: Starting access request tests
    Given we have the state "metadata has been loaded into the system"
    And the session store is empty
    And the claims repository is empty
    And no access requests have been made yet

  Scenario: Requesting access to the dataset A

    Given I am logged in as "Dr. John Doe"
    And I am authenticated as "Dr. John Doe"

    When "Dr. John Doe" requests access to the test dataset "DS_A"
    Then the response status code is "201"
    And "Access Request Created" email was sent to "Central Data Steward"
    And "Access Request Registered" email was sent to "Dr. John Doe"

  Scenario: Requesting access to the dataset B

    When "Dr. John Doe" requests access to the test dataset "DS_B"
    Then the response status code is "201"
    And "Access Request Created" email was sent to "Central Data Steward"
    And "Access Request Registered" email was sent to "Dr. John Doe"

  Scenario: Viewing the pending access requests

    Given I am logged in as "Data Steward"
    And I am authenticated as "Data Steward"

    When "Data Steward" fetches the list of access requests for "all"
    Then the response status code is "200"

    And there is one request for test dataset "DS_A" from "Dr. John Doe"
    And the "status" of the request for dataset "DS_A" is "pending"

    And there is one request for test dataset "DS_B" from "Dr. John Doe"
    And the "status" of the request for dataset "DS_B" is "pending"

  Scenario: Updating an access request

    When "Data Steward" fetches the list of access requests for "DS_B"
    Then there is one request for test dataset "DS_B" from "Dr. John Doe"
    When "Data Steward" updates "ticket id" of the request to "#000"
    Then the response status code is "204"

    When "Data Steward" fetches the list of access requests for "DS_B"
    Then there is one request for test dataset "DS_B" from "Dr. John Doe"
    And the "ticket id" of the request for dataset "DS_B" is "#000"

  Scenario: Granting access to the pending requests
    When "Data Steward" allows the pending requests from "Dr. John Doe"
    Then the user have access to the two test datasets

  Scenario: Confirming the status of access requests

    Given I am logged in as "Data Steward"
    And I am authenticated as "Data Steward"

    When "Data Steward" fetches the list of access requests for "all"
    Then the response status code is "200"

    And there is one request for test dataset "DS_A" from "Dr. John Doe"
    And the "status" of the request for dataset "DS_A" is "allowed"

    And there is one request for test dataset "DS_B" from "Dr. John Doe"
    And the "status" of the request for dataset "DS_B" is "allowed"

    And "Access Request Allowed" email was sent to "Central Data Steward"
    And "Access Request Accepted" email was sent to "Dr. John Doe"
    And set the state to "John Doe is allowed to download the test dataset"
