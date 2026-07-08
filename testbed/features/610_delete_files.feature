
@files @deletion @purge
Feature: 510 Deletion of files
  As an authorized user, I can delete the files from the file backend

  Scenario: Deleting files from the file backend

    Given we have the state "metadata has been re-loaded into the system"
    When the files of the complete datasets are requested to be deleted
    Then the file metadata is removed from the file backend
    # And the file encryption secrets are removed from the vault
    # And the deleted files do not exist in the storage
