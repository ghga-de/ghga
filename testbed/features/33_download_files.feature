@download @files
Feature: 33 Download files
  As a user, I can download files when I have a download token.

  Background:
    Given the download buckets are empty
    And I have an empty working directory for the GHGA connector
    And my Crypt4GH key pair has been stored in two key files

  Scenario: Downloading only vcf files
    Given we have the state "download token for vcf files"
    When I run the GHGA connector download command for "vcf" files
    Then "vcf" files announced in metadata have been downloaded

    When I run the decrypt command of the GHGA connector
    Then all downloaded files have been properly decrypted

  Scenario: Downloading all files
    Given we have the state "download token for all files"
    When I run the GHGA connector download command for "all" files
    Then "all" files announced in metadata have been downloaded

    When I run the decrypt command of the GHGA connector
    Then all downloaded files have been properly decrypted

  Scenario: Finishing the download
    Then set the state to "files have been downloaded"
