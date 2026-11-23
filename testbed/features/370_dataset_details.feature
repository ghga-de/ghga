@browse @metadata @artifacts
Feature: 27 Dataset Details
  As a user, I can show a dataset detail view

  Scenario: View details of dataset A
    When I request the details of "EGADATASET000A" dataset
    Then the response status code is "200"
    And I get the details of "EGADATASET000A" dataset

  Scenario: View details of dataset B
    When I request the details of "EGADATASET000B" dataset
    Then the response status code is "200"
    And I get the details of "EGADATASET000B" dataset

  Scenario: Files excluded from the submission are not part of the dataset
    When I request the details of "EGADATASET000B" dataset
    Then the response status code is "200"
    And no file with alias "RESEARCH_DATA_FILE_10" is listed

  Scenario: View associated sample resource for dataset B
    When I request an associated sample resource for "EGADATASET000B" dataset
    Then the response status code is "200"
    And I get a sample resource

  Scenario: Viewing a non-existing dataset
    When I request the details of "non-existing" dataset
    Then the response status code is "404"
