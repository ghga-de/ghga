@upload
Feature: 204 Upload Box Priority
  As a data steward, I can set the order in which the Data Hubs re-encrypt the files of the upload boxes

  # Features 200 to 203 have deleted or archived their boxes by now, so this feature
  # creates two boxes of its own, both in the primary storage.

  Scenario: Starting the upload box priority journey
    Given the session store is empty
    And I am logged in as "Data Steward"
    And I am authenticated as "Data Steward"
    And I am logged in as "Dr. John Doe"
    And I am authenticated as "Dr. John Doe"

  Scenario Outline: New boxes join the end of the priority list

    When "Data Steward" creates the "<box>" upload box
    Then the response status code is "201"
    And the "<box>" upload box is last in the priority list

    Examples:
      | box    |
      | first  |
      | second |

  Scenario: Data Steward moves the second box before the first

    When "Data Steward" saves the priority list with the "second" upload box before the "first"
    Then the response status code is "200"
    And the saved priority list has the "second" upload box before the "first"
    And the saved priority list has a new version
    And "Data Steward" changed and reordered the saved priority list at the same time
    And FIS stores the saved version of the priority list

  Scenario: RS rejects a save that does not fit the stored list

    When "Data Steward" saves the priority list again with the version it read before
    Then the response status code is "409"

    When "Data Steward" saves the priority list without the "first" upload box
    Then the response status code is "409"

    When "Data Steward" saves the priority list with an unknown box
    Then the response status code is "409"

    When "Data Steward" saves the priority list with the "second" upload box twice
    Then the response status code is "422"

  Scenario: Saving the stored order changes nothing

    When "Data Steward" saves the stored priority list
    Then the response status code is "200"
    And the priority list keeps the saved version

  Scenario Outline: John Doe gets an upload token for each box

    When "Data Steward" grants "John Doe" access to the "<box>" upload box
    Then the response status code is "201"

    When "John Doe" creates an upload work package for the "<box>" upload box
    Then the response status code is "201"
    And the response contains an upload token for the "<box>" upload box

    Examples:
      | box    |
      | first  |
      | second |

  Scenario: The Data Hub re-encrypts the files of the second box first

    # DHFS asks FIS for waiting files every few seconds, so it is held up until all
    # four files wait together. The first box gets its files first, so an order by
    # upload time would fail the check.
    Given I have an empty working directory for the GHGA connector
    And my Crypt4GH key pair has been stored in two key files
    And DHFS is held up by files it cannot find in the "second" upload box

    When two files are uploaded to the "first" upload box
    And two files are uploaded to the "second" upload box
    Then FIS stores the box of each file uploaded to the two boxes

    When the files that hold up DHFS are removed
    Then the files of the "second" upload box are interrogated before those of the "first"
    And the files of each of the two boxes are interrogated in the order of their IDs
