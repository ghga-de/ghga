@dataportal @frontend @upload
Feature: 502 Data Portal Uploads
  As a Data Steward and a user, I can run the upload journey through the Data Portal

  # This UI journey is independent of the API upload boxes (which are already
  # archived by feature 202). It creates its own boxes via the portal, uploads
  # DS_A files, and maps them back to STUDY_A.

  Scenario: Starting the upload journey through the Data Portal

    Given we have no upload boxes yet
    And we have no accession mappings yet

  Scenario: Data Steward logs in to the Data Portal for uploads

    Given the user has logged out of the Data Portal
    And the session store is empty
    And I am logged in as "Data Steward"
    And I am authenticated as "Data Steward"
    And I am logged in to the Data Portal as "Data Steward"

  Scenario Outline: Data Steward creates an upload box

    When I load the admin page "Upload Box Manager"
    Then the upload box manager list is displayed

    When I create an upload box for "<storage>" storage via the portal
    Then the upload box for "<storage>" storage is listed

    When "Data Steward" retrieves the list of data upload boxes
    Then the response contains an upload box ID for "<storage>" storage

    Examples:
      | storage   |
      | primary   |
      | secondary |

  Scenario Outline: Data Steward grants the user upload access

    When I load the admin page "Upload Box Manager"
    And I open the details of the "<storage>" upload box in the portal
    And "John Doe" has been granted upload access for the "<storage>" upload box

    Examples:
      | storage   |
      | primary   |
      | secondary |

  Scenario: User creates an upload token for the primary box

    Given the user has logged out of the Data Portal
    And the session store is empty
    And I am logged in as "Dr. John Doe"
    And I am authenticated as "Dr. John Doe"
    And I am logged in to the Data Portal as "Dr. John Doe"

    When I navigate to the user account page
    And I create an upload token for "primary" storage
    Then the upload token for "primary" storage is available

  Scenario: Files are uploaded to the primary box via the connector

    Given I have an empty working directory for the GHGA connector
    And my Crypt4GH key pair has been stored in two key files
    When "all" files of dataset "DS_A" are uploaded to "primary" storage

  Scenario: User confirms files are uploaded

    When "John Doe" retrieves the list of files uploaded to the box for "primary" storage
    Then the expected item count in response is "7"
    Then all files uploaded to "primary" are "inbox"

  Scenario: User submits the upload

    Given the user has logged out of the Data Portal
    And I am logged in as "Dr. John Doe"
    And I am authenticated as "Dr. John Doe"
    And I am logged in to the Data Portal as "Dr. John Doe"

    When I navigate to the user account page
    And I submit the upload for "primary" storage

  Scenario: Data Steward maps the files and archives the box

    Given the user has logged out of the Data Portal
    And the session store is empty
    And I am logged in as "Data Steward"
    And I am authenticated as "Data Steward"
    And I am logged in to the Data Portal as "Data Steward"

    When "Data Steward" retrieves the list of files uploaded to the box for "primary" storage
    Then all files uploaded to "primary" are "interrogated"

    When I load the admin page "Upload Box Manager"
    And I open the details of the "primary" upload box in the portal
    Then the uploaded files for "DS_A" are listed in the upload box

    When I select the study "DS_A" in the mapping tool
    Then the file mapping is complete for "DS_A"

    When I confirm the mapping and archive the upload box
    Then the "primary" upload box is archived in the portal
