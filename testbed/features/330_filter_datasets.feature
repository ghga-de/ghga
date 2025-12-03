@browse @metadata @mass
Feature: 23 Filter Datasets
  As a user, I can filter the public datasets

  Background:
    Given we have the state "metadata has been loaded into the system"

  Scenario: Verify searching with invalid class
    When I query documents with invalid class name
    Then the response status code is "422"

  Scenario: Filter datasets by EGA accession
    When I filter datasets with EGA accession "EGADATASET000B"
    Then the response status code is "200"
    And I get only dataset "EGADATASET000B" as search result

  Scenario: Filter datasets by study type
    When I filter datasets with the study type "EXOME_SEQUENCING"
    Then the response status code is "200"
    And I get "0" search results

    When I filter datasets with the study type "SYNTHETIC_GENOMICS"
    Then the response status code is "200"
    And I get only dataset "EGADATASET000A" as search result

    When I filter datasets with the study type "WHOLE_GENOME_SEQUENCING"
    Then the response status code is "200"
    And  I get "2" search results

  Scenario: Filter datasets by diagnosis
    When I filter datasets containing the diagnosis "Lymphocytic leukemia"
    Then the response status code is "200"
    And  I get "0" search results

    When I filter datasets containing the diagnosis "Myeloid leukaemia"
    Then the response status code is "200"
    And  I get "2" search results

  Scenario: Filter datasets by platform
    When I filter datasets using the platform "ILLUMINA_HISEQ_X"
    Then the response status code is "200"
    And  I get "0" search results

    When I filter datasets using the platform "454_GS"
    Then the response status code is "200"
    And  I get "2" search results

  Scenario: Filter datasets by FASTQ file format
    When I filter datasets with "FASTQ" research data format
    Then the response status code is "200"
    And  I get "2" search results

 Scenario: Filter datasets by BAM file format
    When I filter datasets with "BAM" research data format
    Then the response status code is "200"
    And  I get "0" search results

  Scenario: Filter datasets for sequencing file
    When I filter datasets with individual supporting file alias
    Then the response status code is "200"
    And I get only dataset "EGADATASET000A" as search result
