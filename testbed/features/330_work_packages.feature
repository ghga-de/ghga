@download @wps
Feature: 33 Work Packages
  As a user, I can create a work package for downloading a file
  and a download token corresponding ot that work package.

  Background:
    Given we have the state "John Doe is allowed to download the test dataset"
    And I am logged in as "Dr. John Doe"
    And I am registered as "Dr. John Doe"
    And I am authenticated as "Dr. John Doe"

  Scenario: Starting work package creation
    Given no work packages have been created yet
    And the test datasets have been announced

  Scenario: Listing datasets available for download
    When "Dr. John Doe" lists the datasets
    Then the response status code is "200"
    And the two test datasets are returned

  Scenario: Creating work package for all files in dataset A
    When "Dr. John Doe" creates a work package for "all" files in dataset "A"
    Then the response status code is "201"
    And the response contains a download token for "all" files in dataset "A"

  Scenario: Creating work package for only vcf files in dataset A
    When "Dr. John Doe" creates a work package for "vcf" files in dataset "A"
    Then the response status code is "201"
    And the response contains a download token for "vcf" files in dataset "A"

  Scenario: Creating work package for all files in dataset B
    When "Dr. John Doe" creates a work package for "all" files in dataset "B"
    Then the response status code is "201"
    And the response contains a download token for "all" files in dataset "B"
