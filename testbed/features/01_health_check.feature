@healthcheck
Feature: 01 Health Check
  Check health endpoints of all services

  Scenario: Check service health endpoints
    Given all the service APIs respond as expected
    Then set the state to "health check is completed"
