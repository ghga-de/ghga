@dataportal @frontend
Feature: 403 Data Portal Download Token
  As a user, I can create download tokens for the available datasets

    Background:

      Given the user has logged out of the Data Portal
      And the session store is empty

    Scenario: Starting download token creation

      Given the user has logged out of the Data Portal
      And the session store is empty
      And no download tokens have been created yet
      And the files to be downloaded have been announced

    Scenario Outline: Creating download token for dataset

      Given I am logged in as "Dr. John Doe"
      And I am logged in to the Data Portal as "Dr. John Doe"

      When I navigate to the user account page
      And I select the "<dataset>" from available datasets
      And I create a download token for "<file_type>" files in dataset "<dataset>"

      Examples:
        | dataset | file_type |
        | DS_A    | all       |
        | DS_A    | vcf       |
