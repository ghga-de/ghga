@upload
Feature: 201 User File Upload
  As a user, I can create upload work packages and upload the files

  Scenario: Starting upload
    Given no upload work packages have been created yet
    And the upload buckets are empty
    And I have an empty working directory for the GHGA connector
    And my Crypt4GH key pair has been stored in two key files
    And no file encryption secrets exist in the vault
    And I am logged in as "Dr. John Doe"
    And I am authenticated as "Dr. John Doe"

  Scenario: User lists the upload boxes available to them
    Given we have the state "upload boxes created and user access granted"
    When "John Doe" retrieves the list of data upload boxes
    Then the response status code is "200"
    And the expected item count in response is "2"

  Scenario Outline: User creates upload work packages

    When "John Doe" creates an upload work package for "<storage>" storage
    Then the response status code is "201"
    And the response contains an upload token for "<storage>" storage

    Examples:
      | storage   |
      | primary   |
      | secondary |

  Scenario: User uploads unwanted files then deletes them

    When uploading a file from "DS_A" to "primary" storage is interrupted
    And "John Doe" retrieves the list of files uploaded to the box for "primary" storage
    Then the expected item count in response is "1"
    And the uploaded file is listed as "cancelled"

    When the interrupted file is re-uploaded to "primary" storage
    And "John Doe" retrieves the list of files uploaded to the box for "primary" storage
    Then the expected item count in response is "1"
    And the uploaded file is listed as "inbox"

    When another file from "DS_A" is uploaded to "primary" storage
    And "John Doe" retrieves the list of files uploaded to the box for "primary" storage
    Then the expected item count in response is "2"
    And the uploaded files are listed as "inbox" or "interrogated"

    When the uploaded files are deleted from "primary" storage
    And "John Doe" retrieves the list of files uploaded to the box for "primary" storage
    Then the expected item count in response is "2"
    And the uploaded files are listed as "cancelled"
    And remove the state "last_uploaded_files"

  Scenario Outline: User uploads the files

    When "<file_type>" files of dataset "<dataset>" are uploaded to "<storage>" storage
    And "John Doe" retrieves the list of files uploaded to the box for "<storage>" storage
    Then the expected item count in response is "<expected_count>"
    And the uploaded files exist in the "inbox" bucket of "<storage>" storage

    Examples:
      | file_type | dataset | storage     | expected_count |
      | all       | DS_A    | primary     | 7              |
      | all       | DS_B    | secondary   | 7              |

  Scenario: Re-uploading already uploaded files

    When "all" files of dataset "DS_A" are uploaded again to "primary" storage
    Then the connector reports the files were already uploaded

  Scenario Outline: User locks the upload box after uploading the files

    When "John Doe" locks the data upload box for "<storage>" storage
    Then the response status code is "204"

    When "John Doe" retrieves the list of files uploaded to the box for "<storage>" storage
    Then all files uploaded to "<storage>" are "interrogated"
    And the uploaded files exist in the "staging" bucket of "<storage>" storage

    Examples:
      | storage   |
      | primary   |
      | secondary |
