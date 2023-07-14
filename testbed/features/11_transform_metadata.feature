@metadata @transformation
Feature: 11 Transform Metadata
  As a data steward, I can run transformation workflow on submitted metadata
  to produce artifacts

  Scenario: Transforming metadata

    Given we have the state "Metadata submission is completed"
    When submitted metadata is transformed
    Then the embedded_public event exists
    And set the state to "Metadata transformation is completed"
