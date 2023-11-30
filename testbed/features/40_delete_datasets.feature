
@metadata @deletion
Feature: 40 Deletion of datasets
  As a data steward, I can delete datasets from the system

  Scenario: Re-uploading metadata after deletion of datasets

    Given we have the state "metadata has been loaded into the system"

    When the artifacts for the complete datasets are removed from the event store
    And metadata is loaded into the system

    Then the stats in the database show only the minimal datasets
    And only the minimal datasets exist as embedded datasets in the database
    And searching for datasets without keyword finds only the minimal datasets
    And only the minimal datasets are known to the work package service
    And no access grants exist any more in the claims repository

  Scenario: Trying to download files again after removal of the datasets

    Given I have an empty working directory for the GHGA connector
    And my Crypt4GH key pair has been stored in two key files
    And we have the state "download token for all files"

    When I run the GHGA connector download command for all files
    Then I get an error message that the token is not valid

  Scenario: Trying to query datasets to create a new download token

    Given we have the state "John Doe is allowed to download the test dataset"
    And I am registered as "Dr. John Doe"
    And I am logged in as "Dr. John Doe"

    When the list of datasets is queried
    Then the response status code is "200"
    And no dataset is returned

    Then remove the state "metadata has been loaded into the system"
    And remove the state "John Doe is allowed to download the test dataset"
    And set the state to "metadata has been re-loaded into the system"
