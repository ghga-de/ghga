@upload
Feature: 202 Upload Completed
  As a user, I can complete the upload and archive files

  Scenario: Starting upload completion
    Given the session store is empty
    And I am logged in as "Data Steward"
    And I am authenticated as "Data Steward"

  Scenario Outline: Submitting the file accession mapping

    When "Data Steward" retrieves the research data upload boxes for "<storage>" storage
    Then the research data upload box state is "locked"

    When files in "<storage>" storage from the "<dataset>" dataset mapped to the "<study>"
    And "Data Steward" submits the mapping for "<study>" files in "<storage>" storage
    Then the response status code is "204"

    Examples:
      | storage   | dataset | study   |
      | primary   | DS_A    | STUDY_A |
      | secondary | DS_B    | STUDY_B |

  Scenario Outline: Archiving the files

    When "Data Steward" retrieves the research data upload boxes for "<storage>" storage
    Then the research data upload box state is "locked"

    When "Data Steward" archives the data upload box for "<storage>" storage
    Then the response status code is "204"

    When "Data Steward" retrieves the list of files uploaded to the box for "<storage>" storage
    Then all files uploaded to "<storage>" are "archived"

    When "Data Steward" retrieves the research data upload boxes for "<storage>" storage
    Then the research data upload box state is "archived"

    Examples:
      | storage   |
      | primary   |
      | secondary |
