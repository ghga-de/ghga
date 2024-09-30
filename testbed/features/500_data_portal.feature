
@dataportal @frontend
Feature: 50 Data Portal UI
  As a user, I can load GHGA Data Portal user interface

  Scenario: Check health of Data Portal UI
    When the data portal ui is accessed
    Then the response status code is "200"

  Scenario: Check content of Data Portal UI
    When the service logo is loaded
    Then the response status code is "200"
    And the content is verified
