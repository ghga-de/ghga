/**
 * Models for the dataset details table
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Experiment, File, Sample } from './dataset-details';

export interface DatasetDetailsTableColumn {
  columnDef: string;
  header: string;
  class?: string;
  accessor: string;
  hidden?: boolean;
}

export const datasetDetailsTableColumns: Record<string, DatasetDetailsTableColumn[]> = {
  experiments: [
    {
      columnDef: 'accession',
      header: 'Experiment ID',
      class: 'w-40',
      accessor: 'accession',
    },
    {
      columnDef: 'ega_accession',
      header: 'EGA ID',
      class: 'w-40',
      accessor: 'ega_accession',
    },
    {
      columnDef: 'title',
      header: 'Title',
      accessor: 'title',
    },
    {
      columnDef: 'description',
      header: 'Description',
      class: 'w-2/5 min-w-xl',
      accessor: 'description',
    },
    {
      columnDef: 'method',
      header: 'Method',
      accessor: 'experiment_method.name',
    },
    {
      columnDef: 'platform',
      header: 'Platform',
      accessor: 'experiment_method.instrument_model',
    },
  ],
  samples: [
    {
      columnDef: 'accession',
      header: 'Sample ID',
      class: 'w-40',
      accessor: 'accession',
    },
    {
      columnDef: 'ega_accession',
      header: 'EGA ID',
      class: 'w-40',
      accessor: 'ega_accession',
    },
    {
      columnDef: 'description',
      header: 'Description',
      class: 'w-2/5 min-w-xl',
      accessor: 'description',
    },
    {
      columnDef: 'status',
      header: 'Status',
      accessor: 'case_control_status',
    },
    {
      columnDef: 'sex',
      header: 'Sex',
      accessor: 'individual.sex',
    },
    {
      columnDef: 'phenotype',
      header: 'Phenotype',
      accessor: 'individual.phenotypic_features_terms',
    },
    {
      columnDef: 'biospecimen_type',
      header: 'Biospecimen type',
      class: 'min-w-44',
      accessor: 'biospecimen_type',
    },
    {
      columnDef: 'tissue',
      header: 'Tissue',
      accessor: 'biospecimen_tissue_term',
    },
  ],
  files: [
    {
      columnDef: 'accession',
      header: 'File ID',
      class: 'w-40',
      accessor: 'accession',
    },
    {
      columnDef: 'ega_accession',
      header: 'EGA ID',
      class: 'w-40',
      accessor: 'ega_accession',
    },
    {
      columnDef: 'name',
      header: 'File name',
      class: 'min-w-48',
      accessor: 'name',
    },
    {
      columnDef: 'type',
      header: 'File type',
      accessor: 'format',
    },
    {
      columnDef: 'origin',
      header: 'File origin',
      accessor: 'file_category',
    },
    {
      columnDef: 'size',
      header: 'File size',
      accessor: 'file_information.size',
    },
    {
      columnDef: 'location',
      header: 'Storage location',
      accessor: 'file_information.storage_alias',
    },
    {
      columnDef: 'hash',
      header: 'File hash',
      accessor: 'file_information.sha256_hash',
    },
  ],
};

export const dataSortingDataAccessor: Record<
  string,
  (arg0: any, key: string) => string | number
> = {
  experiments: (experiment: Experiment, key: string) => {
    switch (key) {
      case 'method':
        return experiment.experiment_method.name;
      case 'platform':
        return experiment.experiment_method.instrument_model;
      default:
        const value = experiment[key as keyof Experiment];
        if (typeof value === 'string' || typeof value === 'number') {
          return value;
        }
        return '';
    }
  },
  samples: (sample: Sample, key: string) => {
    switch (key) {
      case 'status':
        return sample.case_control_status;
      case 'sex':
        return sample.individual.sex;
      case 'phenotype':
        return (sample.individual.phenotypic_features_terms || []).join(', ');
      case 'tissue':
        return sample.biospecimen_tissue_term || '';
      default:
        const value = sample[key as keyof Sample];
        if (typeof value === 'string' || typeof value === 'number') {
          return value;
        }
        return '';
    }
  },
  files: (file: File, key: string) => {
    switch (key) {
      case 'type':
        return file.format;
      case 'origin':
        return file.file_category ?? '';
      case 'size':
        return file.file_information?.size ?? '';
      case 'location':
        return file.file_information?.storage_alias ?? '';
      case 'hash':
        return file.file_information?.sha256_hash ?? '';
      default:
        const value = file[key as keyof File];
        if (typeof value === 'string' || typeof value === 'number') {
          return value;
        }
        return '';
    }
  },
};
