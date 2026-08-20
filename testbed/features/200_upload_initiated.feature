@upload
Feature: 200 Upload Initiated
  As a data steward, I can initiate upload process and grant users to upload their files

  Background:
    Given I am logged in as "Data Steward"
    And I am authenticated as "Data Steward"

  Scenario: Data Steward lists available data upload boxes

    Given no data upload boxes have been created yet
    And the claims repository is empty
    And we have no upload boxes yet

    When "Data Steward" retrieves the list of data upload boxes
    Then the response status code is "200"
    And the expected item count in response is "0"

  Scenario Outline: Data Steward creates data upload box

    When "Data Steward" creates a data upload boxes for "<storage>" storage
    Then the response status code is "201"

    When "Data Steward" retrieves the list of data upload boxes
    Then the response status code is "200"
    And the expected item count in response is "<count>"
    And the response contains an upload box ID for "<storage>" storage

    Examples:
      | storage   | count |
      | primary   | 1     |
      | secondary | 2     |

  Scenario Outline: Data Steward grants user to access data upload box

    Given a data upload box for "primary" storage has been created
    When "Data Steward" lists the access grants for "John Doe"
    Then the response status code is "200"

    When "Data Steward" grants "John Doe" access to upload box for "<storage>" storage
    Then the response status code is "201"
    And the upload claim for "<storage>" storage exists in the claims repository

    When "Data Steward" lists grants for "<storage>" storage
    Then the response status code is "200"

    Examples:
      | storage   |
      | primary   |
      | secondary |

  Scenario: Data Steward deletes a data upload box

    When "Data Steward" creates an extra data upload box for "primary" storage
    Then the response status code is "201"
    And we have an extra data upload box

    When "Data Steward" deletes the extra data upload box
    Then the response status code is "204"

    When "Data Steward" retrieves the list of data upload boxes
    Then the response status code is "200"
    And the expected item count in response is "2"
    And the extra data upload box is no longer listed

  Scenario: Data Steward retrieves data upload boxes by page

    When "Data Steward" retrieves the "last" data upload boxes
    Then the response status code is "200"
    And the expected item count in response is "1"
    And the "secondary" upload box is returned

    When "Data Steward" retrieves the "next" data upload boxes
    Then the response status code is "200"
    And the expected item count in response is "1"
    And the "primary" upload box is returned

  Scenario: Finishing the initiation of upload process

    Then set the state to "upload boxes created and user access granted"
