
@dlq
Feature: 600 Dead Letter Queue
  Unprocessed events should go to the dead letter queue.

  Background:
    Given the dead letter queue is empty

  Scenario: Dataset creation with an invalid schema
    When "dataset creation" event has been published with an invalid schema
    Then "work package service" has published the event to the dead letter queue
    And "dataset information service" has published the event to the dead letter queue

  Scenario: Searchable resource created with an invalid schema
    When "resource creation" event has been published with an invalid schema
    Then "metadata artifact search service" has published the event to the dead letter queue

  Scenario: Access request with an invalid schema
    When "access request" event has been published with an invalid schema
    Then "notification orchestration service" has published the event to the dead letter queue

  Scenario: Notification with an invalid schema
    When "notification" event has been published with an invalid schema
    Then "notification service" has published the event to the dead letter queue

  Scenario: File deletion with an invalid schema
    When "file deletion" event has been published with an invalid schema
    Then "download controller service" has published the event to the dead letter queue
    And "internal file registry service" has published the event to the dead letter queue

  Scenario: Corrected event payload published again
    When "dataset creation" event has been published with an invalid schema
    Then "dataset information service" has published the event to the dead letter queue
    When the corrected dataset creation event has been republished to the dataset information service
    Then the dataset is known to the dataset information service

  Scenario: Deleting the dead letter queue events
    When all events in the dead letter queue have been deleted
    Then there is no event in the dead letter queue
