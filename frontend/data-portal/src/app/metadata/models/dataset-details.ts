/**
 * Short module description
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { FileInformation } from './dataset-information';

export interface DatasetDetails {
  accession: string;
  title: string;
  description: string;
  types: string[];
  ega_accession: string;
  data_access_policy: DataAccessPolicy;
  study: Study;
  process_data_files: File[];
  experiment_method_supporting_files: File[];
  analysis_method_supporting_files: File[];
  individual_supporting_files: File[];
  research_data_files: File[];
  experiments: Experiment[];
  samples: Sample[];
}

interface DataAccessPolicy {
  name: string;
  policy_text: string;
  policy_url: string;
  data_access_committee: {
    alias: string;
    email: string;
  };
}

interface Study {
  accession: string;
  title: string;
  description: string;
  types: string[];
  ega_accession: string;
  publications: Publication[];
}

interface Publication {
  title: string;
  abstract: string;
  author: string;
  year: number;
  journal: string;
  doi: string;
}

export interface File {
  accession: string;
  format: string;
  name: string;
  ega_accession: string;
  file_information?: FileInformation;
  file_category?: string;
}

export interface Experiment {
  accession: string;
  experiment_method: ExperimentMethod;
  title: string;
  description: string;
  ega_accession: string;
}

interface ExperimentMethod {
  accession: string;
  type: string;
  instrument_model: string;
}

interface Sample {
  accession: string;
  individual: Individual;
  name: string;
  description: string;
  case_control_status: string;
  ega_accession: string;
  biospecimen_type: string;
  biospecimen_tissue_term: string;
}

interface Individual {
  sex: string;
  phenotypic_features_terms: string[];
}

export const emptyDatasetDetails: DatasetDetails = {
  accession: '',
  title: '',
  description: '',
  types: [],
  ega_accession: '',
  data_access_policy: {
    name: '',
    policy_text: '',
    policy_url: '',
    data_access_committee: {
      alias: '',
      email: '',
    },
  },
  study: {
    accession: '',
    title: '',
    description: '',
    types: [],
    ega_accession: '',
    publications: [],
  },
  process_data_files: [],
  experiment_method_supporting_files: [],
  analysis_method_supporting_files: [],
  individual_supporting_files: [],
  research_data_files: [],
  experiments: [],
  samples: [],
};
