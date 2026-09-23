@upload
Feature: 202 Requeue Failed Upload
  As a data steward, I can resolve files that failed interrogation,
  either by requeueing them or by deleting them from the upload box

  Background:
    Given I am logged in as "Data Steward"
    And I am authenticated as "Data Steward"

  Scenario: Two files fail interrogation

    Given the data upload box for "primary" storage is unlocked
    When the two largest files of dataset "DS_A" are deleted from "primary" storage
    And those files are uploaded to "primary" storage with corrupted checksums
    Then the "first" file is listed as "failed_interrogation" within "300" seconds
    And the "second" file is listed as "failed_interrogation" within "300" seconds
    And the "first" file reports why it failed
    And FIS holds a failed interrogation report for the "first" file
    And the object of the "first" file is still in the "inbox" bucket of "primary" storage
    And the object of the "second" file is still in the "inbox" bucket of "primary" storage

  Scenario: The box can neither be locked nor archived while files need attention

    When "Data Steward" locks the data upload box for "primary" storage
    Then the response status code is "409"
    And the response names both failed files as needing attention

    When "Data Steward" force-locks the data upload box for "primary" storage
    Then the response status code is "204"

    When "Data Steward" tries to archive the data upload box for "primary" storage
    Then the response status code is "409"
    And the response names both failed files as needing attention

  Scenario: Data Steward requeues a failed file in the locked box

    When "Data Steward" requeues the "first" file in "primary" storage
    Then the response status code is "204"
    And the "first" file is listed as "inbox" within "30" seconds
    And the "first" file no longer reports why it failed
    And the interrogation report for the "first" file has been discarded

  Scenario: The requeued file is interrogated without a second upload

    Then the "first" file is listed as "interrogated" within "300" seconds
    And the object of the "first" file is gone from the "inbox" bucket of "primary" storage

  Scenario: Data Steward deletes the other failed file

    Given the data upload box for "primary" storage is unlocked
    When "Data Steward" deletes the "second" file from "primary" storage
    Then the response status code is "204"
    And the object of the "second" file is gone from the "inbox" bucket of "primary" storage
    And the "second" file is marked as removable in the interrogation service
    And the upload box for "primary" storage holds "6" files

  Scenario: Restoring the box for the rest of the journey

    When the "second" file is uploaded to "primary" storage again
    Then the "second" file is listed as "interrogated" within "300" seconds

    When "Data Steward" locks the data upload box for "primary" storage
    Then the response status code is "204"

    When "Data Steward" retrieves the list of files uploaded to the box for "primary" storage
    Then all files uploaded to "primary" are "interrogated"
