/**
 * Interface for the global metadata summary
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

export interface DatasetSummary {
  title: string;
  accession: string;
  description: string;
  type?: string[];
  studies_summary: StudiesSummary;
  files_summary: FilesSummary;
  samples_summary: SamplesSummary;
  experiments_summary: ExperimentsSummary;
}

interface StudiesSummary {
  count: number;
  stats: {
    accession: string;
    title: string;
  };
}

interface FilesSummary {
  count: number;
  stats: {
    format: { value: string; count: number }[];
  };
}

interface SamplesSummary {
  count: number;
  stats: {
    sex: {
      value: string;
      count: number;
    }[];
    tissues: {
      value: string;
      count: number;
    }[];
    phenotypic_features: {
      value: string;
      count: number;
    }[];
  };
}

interface ExperimentsSummary {
  count: number;
  stats: {
    experiment_methods: { value: string; count: number }[];
  };
}

export const emptyDatasetSummary: DatasetSummary = {
  title: '',
  accession: '',
  description: '',
  type: [],
  studies_summary: { count: 0, stats: { accession: '', title: '' } },
  files_summary: { count: 0, stats: { format: [] } },
  samples_summary: {
    count: 0,
    stats: { sex: [], tissues: [], phenotypic_features: [] },
  },
  experiments_summary: { count: 0, stats: { experiment_methods: [] } },
};
