@healthcheck
Feature: 01 Health Check
  Upfront health check for all services

  Scenario: Check health of all services
    When all service APIs are checked
    Then they report as being healthy
