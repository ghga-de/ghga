@metadata @transformation
Feature: 11 Transform Metadata
  As a data steward, I can run transformation workflow on submitted metadata
  to produce artifacts

  Scenario: Transforming metadata

    Given we have the state "metadata submission is completed"
    When submitted metadata is transformed
    Then the embedded_public event exists

    Then set the state to "metadata transformation is completed"
