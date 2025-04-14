
@dataportal @frontend
Feature: 500 Data Portal
  As a user, I can load GHGA Data Portal user interface

  Scenario: Check health of Data Portal
    When the data portal is accessed
    Then the response status code is "200"

  Scenario: Check favicon of Data Portal
    When the favicon is loaded
    Then the response status code is "200"
    And the favicon is verified
