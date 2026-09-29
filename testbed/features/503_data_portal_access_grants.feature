@dataportal @frontend
Feature: 503 Data Portal Requests
  As a user, I can create dataset access requests and download tokens

    Scenario: Starting data portal access request tests

      Given the claims repository is empty
      And no access requests have been made yet
      And the user has logged out of the Data Portal
      And the session store is empty


    Scenario: Requesting access via dataset detail page

      Given I am logged in as "Dr. John Doe"
      And I am logged in to the Data Portal as "Dr. John Doe"

      When I navigate to the dataset browsing page
      When I select the "DS_A" dataset
      And I open the details of "DS_A" dataset
      And I request access to the "DS_A" dataset


    Scenario: Requesting access via dataset browsing page

      When I navigate to the dataset browsing page
      And I select the "DS_B" dataset
      And I request access to the "DS_B" dataset


    Scenario: Data Steward lists the pending access requests

      Given the user has logged out of the Data Portal
      And the session store is empty
      And I am logged in as "Data Steward"
      And I am logged in to the Data Portal as "Data Steward"

      When I load the admin page "Access Request Manager"
      Then the table shows two "Pending" items for "Dr. John Doe"


    Scenario: Data Steward adds a ticket ID to an access request

      When I load the admin page "Access Request Manager"
      And I filter "access requests" for dataset "DS_A"
      And I select the filtered item
      And I set the ticket ID to "1234567"
      Then the ticket ID "1234567" is saved


    Scenario Outline: Data Steward processes an access request

      When I load the admin page "Access Request Manager"
      And I filter "access requests" for dataset "<dataset>"
      Then the table shows one "Pending" item for "Dr. John Doe"

      When I select the filtered item
      Then I get the access request details on dataset "<dataset>" for "Dr. John Doe"
      And the status of the access request is "Pending"

      When I "<action>" the access request
      And I load the admin page "Access Request Manager"
      And I filter access requests by all statuses
      Then the table shows one "<expected_status>" items for "Dr. John Doe"

      Examples:
      | dataset | action | expected_status  |
      | DS_A    | allow  | Allowed          |
      | DS_B    | deny   | Denied           |
