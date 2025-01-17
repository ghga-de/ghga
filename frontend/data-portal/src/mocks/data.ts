/**
 * Mock data to be used in MSW responses
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

/** TODO: Add type annotations using the models that are also used in the application code. */

/**
 * Metldata API
 */

// get dataset summaries with arbitrary accessions
export const getDatasetSummary = (accession: string) => ({
  ...datasetSummary,
  accession: accession,
});

export const metadataGlobalSummary = {
  resource_stats: {
    ProcessDataFile: {
      count: 532,
      stats: {
        format: [
          { value: 'fastq', count: 124 },
          { value: 'bam', count: 408 },
        ],
      },
    },
    Individual: {
      count: 5432,
      stats: {
        sex: [
          { value: 'Female', count: 1935 },
          { value: 'Male', count: 2358 },
        ],
      },
    },
    ExperimentMethod: {
      count: 1400,
      stats: {
        instrument_model: [
          {
            value: 'Ilumina_test',
            count: 700,
          },
          {
            value: 'HiSeq_test',
            count: 700,
          },
        ],
      },
    },
    Dataset: {
      count: 252,
      stats: {},
    },
  },
};

/**
 * MASS API
 */

export const searchResults = {
  facets: [
    {
      key: 'studies.type',
      name: 'Study Type',
      options: [
        { value: 'Option 1', count: 62 },
        { value: 'Option 2', count: 37 },
      ],
    },
    {
      key: 'type',
      name: 'Dataset Type',
      options: [
        { value: 'Test dataset type 1', count: 12 },
        { value: 'Test dataset type 2', count: 87 },
      ],
    },
  ],
  count: 25, // just to test the paginator
  hits: [
    {
      id_: 'GHGAD588887987',
      content: {
        accession: 'GHGAD588887987',
        ega_accession: 'EGAD588887987',
        title: 'Test dataset for details',
        description:
          'Test dataset for Metadata Repository get dataset details call. Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Vel risus commodo viverra maecenas accumsan lacus vel. Sit amet risus nullam eget felis eget nunc lobortis mattis. Iaculis at erat pellentesque adipiscing commodo. Volutpat consequat mauris nunc congue. At lectus urna duis convallis convallis tellus id interdum velit. Gravida cum sociis natoque penatibus et. Mauris in aliquam sem fringilla ut morbi. Ultrices gravida dictum fusce ut. At consectetur lorem donec massa sapien faucibus et molestie.',
        types: ['Test dataset type 1'],
      },
    },
    {
      id_: 'GHGAD588887988',
      content: {
        accession: 'GHGAD588887988',
        ega_accession: 'EGAD588887988',
        title: 'Test dataset for details',
        description:
          'Test dataset for Metadata Repository get dataset details call. Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Vel risus commodo viverra maecenas accumsan lacus vel. Sit amet risus nullam eget felis eget nunc lobortis mattis. Iaculis at erat pellentesque adipiscing commodo. Volutpat consequat mauris nunc congue. At lectus urna duis convallis convallis tellus id interdum velit. Gravida cum sociis natoque penatibus et. Mauris in aliquam sem fringilla ut morbi. Ultrices gravida dictum fusce ut. At consectetur lorem donec massa sapien faucibus et molestie.',
        types: ['Test dataset type 1'],
      },
    },
    {
      id_: 'GHGAD588887989',
      content: {
        accession: 'GHGAD588887989',
        ega_accession: 'EGAD588887989',
        title: 'Test dataset for details',
        description:
          'Test dataset for Metadata Repository get dataset details call. Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Vel risus commodo viverra maecenas accumsan lacus vel. Sit amet risus nullam eget felis eget nunc lobortis mattis. Iaculis at erat pellentesque adipiscing commodo. Volutpat consequat mauris nunc congue. At lectus urna duis convallis convallis tellus id interdum velit. Gravida cum sociis natoque penatibus et. Mauris in aliquam sem fringilla ut morbi. Ultrices gravida dictum fusce ut. At consectetur lorem donec massa sapien faucibus et molestie.',
        types: ['Test dataset type 1'],
      },
    },
  ],
};

export const datasetSummary = {
  accession: 'GHGAD588887987',
  description:
    'Test dataset for Metadata Repository get dataset details call. Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Vel risus commodo viverra maecenas accumsan lacus vel. Sit amet risus nullam eget felis eget nunc lobortis mattis. Iaculis at erat pellentesque adipiscing commodo. Volutpat consequat mauris nunc congue. At lectus urna duis convallis convallis tellus id interdum velit. Gravida cum sociis natoque penatibus et. Mauris in aliquam sem fringilla ut morbi. Ultrices gravida dictum fusce ut. At consectetur lorem donec massa sapien faucibus et molestie.',
  type: ['Test Type'],
  title: 'Test dataset for details',
  dac_email: 'test[at]test[dot]de;',
  samples_summary: {
    count: 3,
    stats: {
      sex: [
        { value: 'Female', count: 1 },
        { value: 'Male', count: 1 },
      ],
      tissues: [
        { value: 'metastasis', count: 1 },
        { value: 'tumor', count: 2 },
      ],
      phenotypic_features: [
        { value: 'Test Phenotype 1', count: 2 },
        { value: 'Test Phenotype 2', count: 1 },
      ],
    },
  },
  studies_summary: {
    count: 1,
    stats: {
      accession: ['TEST18666800'],
      title: ['Test Study'],
    },
  },
  experiments_summary: {
    count: 14,
    stats: {
      experiment_methods: [
        {
          value: 'Ilumina_test',
          count: 10,
        },
        { value: 'HiSeq_test', count: 4 },
      ],
    },
  },
  files_summary: {
    count: 27,
    stats: {
      format: [
        { value: 'FASTQ', count: 22 },
        { value: 'BAM', count: 5 },
      ],
      size: 434543980,
    },
  },
};
