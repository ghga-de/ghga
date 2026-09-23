@upload
Feature: 202 Requeue Failed Upload
  As a data steward, I can requeue a file that failed interrogation,
  so that it is interrogated again without the submitter uploading it a second time

  Background:
    Given I am logged in as "Data Steward"
    And I am authenticated as "Data Steward"

  Scenario: A file fails interrogation

    Given the data upload box for "primary" storage is unlocked
    When the largest file of dataset "DS_A" is deleted from "primary" storage
    And that file is uploaded to "primary" storage with a corrupted expected checksum
    Then the file is listed as "failed_interrogation" within "300" seconds
    And the file reports why it failed
    And the uploaded object is still in the "inbox" bucket of "primary" storage

  Scenario: Data Steward requeues the failed file

    When "Data Steward" requeues the failed file in "primary" storage
    Then the response status code is "204"
    And the file is listed as "inbox" within "30" seconds
    And the file no longer reports why it failed
    And the interrogation report for the file has been discarded

  Scenario: The requeued file is interrogated without a second upload

    Then the file is listed as "interrogated" within "300" seconds
    And the uploaded object is gone from the "inbox" bucket of "primary" storage

    When "Data Steward" locks the data upload box for "primary" storage again
    Then the response status code is "204"

    When "Data Steward" retrieves the list of files uploaded to the box for "primary" storage
    Then all files uploaded to "primary" are "interrogated"
