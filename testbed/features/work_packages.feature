@download @wps
Feature: 31 Work Packages
  As a user, I can create a work package for downloading a file
  and a download token corresponding ot that work package.

  Scenario: Creating a download token

    Given no work packages have been created yet
    And the test dataset has been announced
    And I am logged in as "Dr. John Doe"

    When the list of datasets is queried

    Then the response status code is "200"
    And the test dataset is in the response list

    When a work package for the test dataset is created
    Then the response status code is "201"
    And the response contains a work package access token
