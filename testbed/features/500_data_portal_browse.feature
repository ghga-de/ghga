
@dataportal @frontend
Feature: 400 Data Portal Browsing
  As a user, I can browse in the data portal without logging in

  Background:
    Given I load the homepage

  Scenario: Homepage content
    Then the homepage content is displayed
    And the global statistics are available

  Scenario: Filtering and searching datasets
    When I navigate to the dataset browsing page

    When I filter datasets by "SYNTHETIC_GENOMICS"
    Then only the "DS_A" dataset is displayed

    When I clear the applied filters
    Then all the available datasets are displayed

    When I search for "DS_B"
    Then only the "DS_B" dataset is displayed

  Scenario: Browsing datasets
    When I navigate to the dataset browsing page
    Then all the available datasets are displayed

    When I select the "DS_B" dataset
    Then the summary of the "DS_B" dataset is displayed

  Scenario: Datasets details
    When I navigate to the dataset browsing page

    When I select the "DS_A" dataset
    And I open the details of "DS_A" dataset
    Then the details of the "DS_A" dataset are displayed
    And the summary tables for the "DS_A" dataset are displayed

  Scenario: Datasets study page

    When I navigate to the dataset browsing page

    When I select the "DS_A" dataset
    And I open the details of "DS_A" dataset

    When I click the "study" link of the "DS_A"
    Then the "study" page of the "DS_A" is loaded

  # TODO Scenario: Request access - You must be logged in to perform this action
  # TODO Scenario: Metadata download
