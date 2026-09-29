@upload
Feature: 202 Requeue Failed Upload
  As a data steward, I can resolve files that failed interrogation,
  either by requeueing them or by deleting them from the upload box

  Background:
    Given the session store is empty
    And I am logged in as "Data Steward"
    And I am authenticated as "Data Steward"

  Scenario: Three files fail interrogation

    Given the data upload box for "primary" storage is unlocked
    When the three largest files of dataset "DS_A" are deleted from "primary" storage
    And those files are uploaded to "primary" storage with corrupted checksums
    Then the "first" file is listed as "failed_interrogation" within "60" seconds
    And the "second" file is listed as "failed_interrogation" within "60" seconds
    And the "third" file is listed as "failed_interrogation" within "60" seconds
    And the "first" file reports why it failed
    And FIS holds a failed interrogation report for the "first" file
    And FIS holds a failed interrogation report for the "third" file
    And the object of the "first" file is still in the "inbox" bucket of "primary" storage
    And the object of the "second" file is still in the "inbox" bucket of "primary" storage

  Scenario: The box can neither be locked nor archived while files need attention

    When "Data Steward" locks the data upload box for "primary" storage
    Then the response status code is "409"
    And the response names all failed files as needing attention

    When "Data Steward" force-locks the data upload box for "primary" storage
    Then the response status code is "204"

    When "Data Steward" tries to archive the data upload box for "primary" storage
    Then the response status code is "409"
    And the response names all failed files as needing attention

  @dataportal @frontend
  Scenario: Data Steward requeues a failed file in the locked box via the portal

    Given I am logged in to the Data Portal as "Data Steward"
    When I open the upload box for "primary" storage in the portal
    Then the "first" file is offered a retry in the portal
    And the "second" file is offered a retry in the portal
    And the "third" file is offered a retry in the portal
    And the portal offers to retry all failed re-encryptions

    When I retry the re-encryption of the "first" file in the portal
    Then the portal reports that the "first" file has been queued for re-encryption
    And the "first" file is shown as "re-encrypting…" in the portal
    And the "first" file has reached the "inbox" state within "30" seconds
    And the "first" file no longer reports why it failed
    And the interrogation report for the "first" file has been discarded

    When "Data Steward" requeues the "first" file in "primary" storage
    Then the response status code is "409"
    And the user has logged out of the Data Portal

  Scenario: The requeued file is interrogated without a second upload

    Then the "first" file is listed as "interrogated" within "60" seconds
    And the object of the "first" file is gone from the "inbox" bucket of "primary" storage

  Scenario: Data Steward deletes a failed file

    Given the data upload box for "primary" storage is unlocked
    When "Data Steward" deletes the "second" file from "primary" storage
    Then the response status code is "204"
    And the object of the "second" file is gone from the "inbox" bucket of "primary" storage
    And the "second" file is marked as removable in the interrogation service
    And the upload box for "primary" storage holds "6" files

  @dataportal @frontend
  Scenario: Data Steward requeues all failed files of the box via the portal

    Given I am logged in to the Data Portal as "Data Steward"
    When I open the upload box for "primary" storage in the portal
    Then the "third" file is offered a retry in the portal
    And the portal offers to retry all failed re-encryptions

    When I retry all failed re-encryptions in the portal
    Then the portal has requeued only the "third" file
    And the portal reports "1 file queued for re-encryption."
    And the "third" file is shown as "re-encrypting…" in the portal
    And the portal no longer offers to retry all failed re-encryptions
    And the "third" file has reached the "inbox" state within "30" seconds
    And the "third" file no longer reports why it failed
    And the interrogation report for the "third" file has been discarded
    And the user has logged out of the Data Portal

  Scenario: Restoring the box for the rest of the journey

    When the "second" file is uploaded to "primary" storage again
    Then the "second" file is listed as "interrogated" within "60" seconds
    And the "third" file is listed as "interrogated" within "60" seconds

    When "Data Steward" locks the data upload box for "primary" storage
    Then the response status code is "204"

    When "Data Steward" retrieves the list of files uploaded to the box for "primary" storage
    Then all files uploaded to "primary" are "interrogated"
