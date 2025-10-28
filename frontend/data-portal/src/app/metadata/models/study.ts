/**
 * Interface for the study datatype
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

export interface Study {
  accession: string;
  alias: string;
  title: string;
  description: string;
  types: string[];
  ega_accession: string;
  affiliations: string[];
  datasets: string[];
  publications: string[];
}

export const emptyStudy: Study = {
  accession: '',
  alias: '',
  title: '',
  description: '',
  types: [],
  ega_accession: '',
  affiliations: [],
  datasets: [],
  publications: [],
};
