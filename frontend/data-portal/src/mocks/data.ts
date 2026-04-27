/**
 * Mock data to be used in MSW responses
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { AccessGrant } from '@app/access-requests/models/access-requests';
import { RegisteredUser, UserStatus } from '@app/auth/models/user';
import { IvaState, IvaType, UserWithIva } from '@app/ivas/models/iva';
import { DatasetDetailsRaw } from '@app/metadata/models/dataset-details';
import { DatasetInformation } from '@app/metadata/models/dataset-information';
import { DatasetSummary } from '@app/metadata/models/dataset-summary';
import { BaseGlobalSummary } from '@app/metadata/models/global-summary';
import { SearchResults } from '@app/metadata/models/search-results';
import { Study } from '@app/metadata/models/study';
import { BaseStorageLabels } from '@app/metadata/models/well-known-values';
import { BoxRetrievalResults, UploadBoxState } from '@app/upload/models/box';
import { FileUploadWithAccession } from '@app/upload/models/file-upload';
import { GrantWithBoxInfo } from '@app/upload/models/grant';
import { DatasetWithExpiration } from '@app/work-packages/models/dataset';
import { WorkPackageResponse } from '@app/work-packages/models/work-package';

/**
 * Users
 */

export const users: RegisteredUser[] = [
  {
    id: 'doe@test.dev',
    ext_id: 'aacaffeecaffeecaffeecaffeecaffeecaffeeaad@lifescience-ri.eu',
    name: 'John Doe',
    title: 'Dr.',
    email: 'doe@home.org',
    roles: ['data_steward'],
    status: UserStatus.active,
    registration_date: '2022-06-01T00:00:00',
  },
  {
    id: 'roe@test.dev',
    ext_id: 'aacaffeecaffeecaffeecaffeecaffeecaffeeaae@lifescience-ri.eu',
    name: 'Jane Roe',
    title: 'Prof.',
    email: 'roe@home.org',
    roles: [],
    status: UserStatus.active,
    registration_date: '2023-01-01T00:00:00',
  },
  {
    id: 'mar@test.dev',
    ext_id: 'aacaffeecaffeecaffeecaffeecaffeecaffeeaaf@lifescience-ri.eu',
    name: 'Joan Mar',
    title: 'Dr.',
    email: 'mar@home.org',
    roles: [],
    status: UserStatus.active,
    registration_date: '2023-03-01T00:00:00',
  },
  {
    id: 'jekyll@test.dev',
    ext_id: 'aacaffeecaffeecaffeecaffeecaffeecafjekyll@lifescience-ri.eu',
    name: 'Henry Jekyll',
    title: 'Dr.',
    email: 'jekyll@home.org',
    roles: [],
    status: UserStatus.active,
    registration_date: '2024-04-01T00:00:00',
  },
  {
    id: 'hyde@test.dev',
    ext_id: 'aacaffeecaffeecaffeecaffeecaffeecaffehyde@lifescience-ri.eu',
    name: 'Henry Jekyll',
    title: 'Dr.',
    email: 'jekyll@home.org',
    roles: [],
    status: UserStatus.active,
    registration_date: '2024-04-02T00:00:00',
  },
  {
    id: 'fred.flintstone@test.dev',
    ext_id: 'caffeecaffeecaffeecaffeecaffeecaffeeaafaa@lifescience-ri.eu',
    name: 'Fred Flintstone',
    title: null,
    email: 'fred@flintstones.org',
    roles: [],
    status: UserStatus.active,
    status_change: {
      previous: 'inactive',
      by: 'doe@test.dev',
      context: '',
      change_date: '2025-01-10T00:00:00',
    },
    registration_date: '2023-08-15T00:00:00',
  },
  {
    id: 'wilma.flintstone@test.dev',
    ext_id: 'caffeecaffeecaffeecaffeecaffeecaffeeabaaa@lifescience-ri.eu',
    name: 'Wilma Flintstone',
    title: null,
    email: 'wilma@flintstones.org',
    roles: [],
    status: UserStatus.active,
    registration_date: '2023-08-15T00:00:00',
  },
  {
    id: 'barney.rubble@test.dev',
    ext_id: 'caffeecaffeecaffeecaffeecaffeecaffeeacdaa@lifescience-ri.eu',
    name: 'Barney Rubble',
    title: null,
    email: 'barney@flintstones.org',
    roles: [],
    status: UserStatus.inactive,
    status_change: {
      previous: 'active',
      by: 'doe@test.dev',
      context: 'Mockery of other users',
      change_date: '2025-01-10T00:00:00',
    },
    registration_date: '2024-08-15T00:00:00',
  },
  {
    id: 'bamm-bamm.flintstone@test.dev',
    ext_id: 'caffeecaffeecaffeecaffeecaffeecaffeeadeaa@lifescience-ri.eu',
    name: 'Jeffrey Spencer Slate Sr.',
    title: 'Prof.',
    email: 'jeff@flintstones.org',
    roles: ['data_steward'],
    status: UserStatus.inactive,
    status_change: {
      previous: 'active',
      by: 'unknown',
      context: 'Clubbing of other users',
      change_date: '2025-01-10T00:00:00',
    },
    registration_date: '2024-09-01T00:00:00',
  },
];

/**
 * IVAs
 */

export const allIvas: UserWithIva[] = [
  {
    id: '0063effb-2c43-4948-ba6f-f15425cb72d7',
    type: IvaType.InPerson,
    value: 'Hauptstr. 321',
    changed: '2024-01-01T00:00:00',
    state: IvaState.CodeRequested,
    user_id: 'roe@test.dev',
    user_name: 'Prof. Jane Roe',
    user_email: 'roe@home.org',
  },
  {
    id: '32b50c92-489f-4418-ace8-e7552e3cf36d',
    type: IvaType.Phone,
    value: '+491234567890000',
    changed: '2024-03-01T00:00:00',
    state: IvaState.Unverified,
    user_id: 'doe@test.dev',
    user_name: 'Dr. John Doe',
    user_email: 'doe@home.org',
  },
  {
    id: '783d9682-d5e5-4ce7-9157-9eeb53a1e9ba',
    type: IvaType.Phone,
    value: '+441234567890004',
    changed: '2024-02-01T00:00:00',
    state: IvaState.Verified,
    user_id: 'doe@test.dev',
    user_name: 'Dr. John Doe',
    user_email: 'doe@home.org',
  },
  {
    id: 'fc3c0ad8-01a4-4eb1-b8f3-40b04bb4bcb2',
    type: IvaType.PostalAddress,
    value:
      'c/o Weird Al Yankovic, Dr. John Doe, Wilhelmstraße 123, Apartment 25, Floor 2, 72072 Tübingen, Baden-Württemberg, Deutschland',
    changed: '2024-04-01T00:00:00',
    state: IvaState.CodeTransmitted,
    user_id: 'doe@test.dev',
    user_name: 'Dr. John Doe',
    user_email: 'doe@home.org',
  },
  {
    id: '347368b5-718e-49ba-80ad-bc128e83b609',
    type: IvaType.InPerson,
    value: 'Mathematikon',
    changed: '2024-05-01T00:00:00',
    state: IvaState.CodeCreated,
    user_id: 'roe@test.dev',
    user_name: 'Prof. Jane Roe',
    user_email: 'roe@home.org',
  },
  {
    id: '8264bc37-ed25-4d66-affa-fa61c59ff246',
    type: IvaType.InPerson,
    value: 'Leicester Square, London',
    changed: '2025-05-01T00:00:00',
    state: IvaState.CodeRequested,
    user_id: 'jekyll@test.dev',
    user_name: 'Dr. Henry Jekyll',
    user_email: 'jekyll@home.org',
  },
  {
    id: '8366a278-58cf-42fa-ad40-3a8142e2c183',
    type: IvaType.InPerson,
    value: 'Leicester Square, London',
    changed: '2025-05-02T00:00:00',
    state: IvaState.CodeRequested,
    user_id: 'hyde@test.dev',
    user_name: 'Dr. Henry Jekyll',
    user_email: 'jekyll@home.org',
  },
  {
    id: 'd88712a6-c687-4ec6-8937-488d634f47c6',
    type: IvaType.Phone,
    value: '+441234567890005',
    changed: '2025-02-01T00:00:00',
    state: IvaState.Verified,
    user_id: 'mar@test.dev',
    user_name: 'Dr. Joan Mar',
    user_email: 'mar@home.org',
  },
];

export const allIvasOfDoe = allIvas.filter((iva) => iva.user_id === 'doe@test.dev');
export const allIvasOfRoe = allIvas.filter((iva) => iva.user_id === 'roe@test.dev');
export const allIvasOfMar = allIvas.filter((iva) => iva.user_id === 'mar@test.dev');

/**
 * Metldata API
 */

// get dataset summaries with arbitrary accessions
// get dataset summaries with arbitrary accessions
export const getDatasetSummary = (accession: string) => {
  const summary = structuredClone(datasetSummary);
  if (accession === 'GHGAD12345678901236') {
    // this is to test the rendering of empty stats
    summary.samples_summary.stats.phenotypic_features =
      summary.experiments_summary.stats.experiment_methods =
      summary.files_summary.stats.format =
      summary.samples_summary.stats.tissues =
        [];
  }
  summary.accession = accession;
  return summary;
};

// get embedded datasets with arbitrary accessions
export const getDatasetDetails = (accession: string) => {
  let ega_accession: string | undefined = accession.replace('GHGA', 'EGA');

  // the following two IDs have special ega accessions for testing. Generally we just want some value here but these two datasets are used to test the absence of ega accession
  if (accession === 'GHGAD12345678901237') {
    ega_accession = '   ';
  }
  if (accession === 'GHGAD12345678901238') {
    ega_accession = undefined;
  }

  return {
    ...datasetDetails,
    accession: accession,
    ega_accession,
  };
};

export const metadataGlobalSummary: BaseGlobalSummary = {
  resource_stats: {
    AnalysisMethodSupportingFile: {
      count: 5,
      stats: {
        format: [{ value: 'txt', count: 5 }],
      },
    },
    ExperimentMethodSupportingFile: {
      count: 19,
      stats: {
        format: [
          { value: 'txt', count: 7 },
          { value: 'bam', count: 12 },
        ],
      },
    },
    IndividualSupportingFile: {
      count: 25,
      stats: {
        format: [
          { value: 'fastq', count: 1 },
          { value: 'bam', count: 7 },
          { value: 'zip', count: 17 },
        ],
      },
    },
    ProcessDataFile: {
      count: 532,
      stats: {
        format: [
          { value: 'fastq', count: 124 },
          { value: 'bam', count: 408 },
        ],
      },
    },
    ResearchDataFile: {
      count: 122,
      stats: {
        format: [
          { value: 'fastq', count: 87 },
          { value: 'bam', count: 35 },
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
            value: 'HiSeq_test',
            count: 150,
          },
          {
            value: 'Illumina_test_6002',
            count: 50,
          },
          {
            value: 'Illumina_test_6003',
            count: 250,
          },
          {
            value: 'Illumina_test_6004',
            count: 50,
          },
          {
            value: 'Illumina_test_test_6000_6001_6002_6003',
            count: 100,
          },
          {
            value: 'Illumina_test_test_6001',
            count: 100,
          },
          {
            value: 'Illumina_test_test',
            count: 100,
          },
          {
            value: 'Nexttest_100',
            count: 100,
          },
          {
            value: 'Nexttest_102',
            count: 100,
          },
          {
            value: 'Nexttest_103',
            count: 100,
          },
          {
            value: 'Nexttest_104',
            count: 300,
          },
        ],
      },
    },
    Dataset: {
      count: 252,
    },
  },
};

export const datasetSummary: DatasetSummary = {
  accession: 'GHGAD12345678901234',
  description:
    'This is the test dataset description. Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.\nVel risus commodo viverra maecenas accumsan lacus vel. Sit amet risus nullam eget felis eget nunc lobortis mattis. Iaculis at erat pellentesque adipiscing commodo. Volutpat consequat mauris nunc congue. At lectus urna duis convallis convallis tellus id interdum velit. Gravida cum sociis natoque penatibus et. Mauris in aliquam sem fringilla ut morbi. Ultrices gravida dictum fusce ut. At consectetur lorem donec massa sapien faucibus et molestie.',
  types: ['Test Type Lorem ipsum dolor sit amet, consectetur adipiscing elit'],
  title: 'Test dataset for details',
  dac_email: 'test@some.dac.org',
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
        {
          value:
            'Test Phenotype 1 Lorem ipsum dolor sit amet, consectetur adipiscing elit',
          count: 2,
        },
        {
          value:
            'Test Phenotype 2 Lorem ipsum dolor sit amet, consectetur adipiscing elit',
          count: 1,
        },
        {
          value:
            'Test Phenotype 3 Lorem ipsum dolor sit amet, consectetur adipiscing elit',
          count: 1,
        },
      ],
    },
  },
  studies_summary: {
    count: 1,
    stats: {
      accession: ['GHGAS12345678901234'],
      title: ['Test Study'],
    },
  },
  experiments_summary: {
    count: 14,
    stats: {
      experiment_methods: [
        {
          value: 'Illumina_test',
          count: 10,
        },
        { value: 'HiSeq_test', count: 4 },
      ],
    },
  },
  files_summary: {
    count: 30,
    stats: {
      format: [
        { value: 'FASTQ', count: 22 },
        { value: 'BAM', count: 5 },
        { value: 'TXT', count: 2 },
        { value: 'PDF', count: 1 },
      ],
    },
  },
};

export const datasetDetails: DatasetDetailsRaw = {
  accession: 'GHGAD12345678901234',
  title: 'Test dataset for details',
  description:
    'Test dataset with some details for testing. Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Vel risus commodo viverra maecenas accumsan lacus vel. Sit amet risus nullam eget felis eget nunc lobortis mattis. Iaculis at erat pellentesque adipiscing commodo. Volutpat consequat mauris nunc congue. At lectus urna duis convallis convallis tellus id interdum velit. Gravida cum sociis natoque penatibus et. Mauris in aliquam sem fringilla ut morbi. Ultrices gravida dictum fusce ut. At consectetur lorem donec massa sapien faucibus et molestie.',
  types: ['Test Type Lorem ipsum dolor sit amet, consectetur adipiscing elit'],
  ega_accession: 'EGAD12345678901',
  data_access_policy: {
    name: 'DAP 1',
    data_access_committee: {
      alias: 'Test DAC',
      email: 'test[at]test[dot]de',
    },
    policy_text: `Test policy text. Neque volutpat ac tincidunt vitae semper quis. Mi eget mauris pharetra et ultrices neque ornare. Consectetur purus ut faucibus pulvinar elementum. Tortor at risus viverra adipiscing. Aliquam eleifend mi in nulla. Orci ac auctor augue mauris augue neque gravida. Rutrum tellus pellentesque eu tincidunt tortor aliquam nulla. Turpis massa tincidunt dui ut ornare lectus sit amet. Laoreet suspendisse interdum consectetur libero id faucibus nisl tincidunt. Auctor eu augue ut lectus arcu bibendum. Aenean et tortor at risus.\n
      Diam phasellus vestibulum lorem sed risus ultricies tristique nulla aliquet. Tempor orci eu lobortis elementum nibh. Tincidunt praesent semper feugiat nibh sed pulvinar proin gravida. Sed nisi lacus sed viverra tellus. Orci dapibus ultrices in iaculis nunc sed augue. Gravida dictum fusce ut placerat orci nulla pellentesque dignissim enim. Facilisi cras fermentum odio eu. Est placerat in egestas erat. At ultrices mi tempus imperdiet nulla malesuada. Tincidunt arcu non sodales neque. Mi bibendum neque egestas congue quisque.\n
      Pharetra vel turpis nunc eget lorem dolor sed. Commodo quis imperdiet massa tincidunt nunc pulvinar sapien et. Vel pretium lectus quam id leo. Ornare suspendisse sed nisi lacus sed viverra. Magna etiam tempor orci eu lobortis elementum. Aliquam nulla facilisi cras fermentum. Rutrum tellus pellentesque eu tincidunt tortor aliquam nulla facilisi cras. Nam at lectus urna duis. Nunc scelerisque viverra mauris in aliquam sem fringilla ut morbi. At elementum eu facilisis sed odio morbi quis commodo odio. Amet nisl purus in mollis nunc sed id. Tristique sollicitudin nibh sit amet. Arcu risus quis varius quam quisque id diam. Nisl tincidunt eget nullam non. Bibendum arcu vitae elementum curabitur vitae. Vitae aliquet nec ullamcorper sit amet risus nullam eget felis.\n
      Cum sociis natoque penatibus et magnis. Quam lacus suspendisse faucibus interdum. Lorem dolor sed viverra ipsum. Non pulvinar neque laoreet suspendisse interdum consectetur. Sit amet consectetur adipiscing elit ut aliquam. Mi ipsum faucibus vitae aliquet nec. Eget egestas purus viverra accumsan in nisl nisi scelerisque eu. Vel orci porta non pulvinar neque laoreet suspendisse interdum consectetur. Justo nec ultrices dui sapien eget mi proin sed. Lacus viverra vitae congue eu consequat. Purus viverra accumsan in nisl nisi scelerisque eu ultrices vitae. Pretium aenean pharetra magna ac placerat vestibulum lectus mauris. Consequat interdum varius sit amet mattis vulputate. Venenatis cras sed felis eget velit. Cursus metus aliquam eleifend mi in nulla posuere sollicitudin aliquam. Tristique senectus et netus et malesuada fames ac. Massa enim nec dui nunc mattis enim ut tellus elementum.`,
    policy_url: 'https://test.com',
    data_use_permission_term: 'GENERAL_RESEARCH_USE',
    data_use_permission_id: 'DUO:0000042',
    data_use_modifier_terms: [
      'PUBLICATION_REQUIRED',
      'INSTITUTION_SPECIFIC_RESTRICTION',
    ],
    data_use_modifier_ids: ['DUO:0000019', 'DUO:0000028'],
  },
  study: {
    accession: 'GHGAS12345678901234',
    ega_accession: 'EGAS12345678901',
    types: ['test_genomics_Lorem ipsum dolor sit amet, consectetur adipiscing elit'],
    title: 'Test Study',
    description:
      'Test study description. Pharetra convallis posuere morbi leo urna molestie. Ut faucibus pulvinar elementum integer. Nec nam aliquam sem et tortor. Pretium viverra suspendisse potenti nullam ac. Commodo sed egestas egestas fringilla. Tincidunt dui ut ornare lectus sit. Amet massa vitae tortor condimentum lacinia quis vel eros donec. Feugiat pretium nibh ipsum consequat. Pulvinar etiam non quam lacus suspendisse faucibus interdum. Aliquam sem et tortor consequat id.',
    publications: [
      {
        doi: '10.1109/5.771073',
        abstract:
          'Test publication abstract. Varius duis at consectetur lorem donec massa sapien faucibus. Amet porttitor eget dolor morbi non arcu. Urna nec tincidunt praesent semper feugiat nibh sed pulvinar proin. Accumsan tortor posuere ac ut consequat semper viverra nam. Vestibulum lorem sed risus ultricies. Sed odio morbi quis commodo odio. Viverra tellus in hac habitasse. Vestibulum mattis ullamcorper velit sed ullamcorper morbi tincidunt. Egestas tellus rutrum tellus pellentesque eu tincidunt tortor. Faucibus purus in massa tempor nec feugiat nisl. Nibh cras pulvinar mattis nunc. In tellus integer feugiat scelerisque varius morbi enim nunc faucibus. Vestibulum mattis ullamcorper velit sed ullamcorper morbi tincidunt. Vitae et leo duis ut diam quam. Egestas fringilla phasellus faucibus scelerisque eleifend donec pretium vulputate. Cras pulvinar mattis nunc sed blandit libero volutpat sed cras. Id diam maecenas ultricies mi eget mauris. Pulvinar etiam non quam lacus suspendisse faucibus interdum posuere lorem. Consequat ac felis donec et.',
        title: 'Test publication',
        author: 'Test author',
        journal: 'Test journal',
        year: 2023,
      },
      {
        doi: '10.1109/5.771074',
      },
    ],
  },
  process_data_files: [
    {
      accession: 'GHGAF12345678901234',
      ega_accession: 'EGAF12345678901',
      name: 'Process data file 1',
      format: 'BAM',
    },
    {
      accession: 'GHGAF12345678901235',
      ega_accession: 'EGAF12345678902',
      name: 'Process data file 2',
      format: 'BAM',
    },
    {
      accession: 'GHGAF12345678901236',
      ega_accession: 'EGAF12345678903',
      name: 'Process data file 3',
      format: 'BAM',
    },
    {
      accession: 'GHGAF12345678901237',
      ega_accession: 'EGAF12345678904',
      name: 'Process data file 4',
      format: 'BAM',
    },
    {
      accession: 'GHGAF12345678901238',
      ega_accession: 'EGAF12345678905',
      name: 'Process data file 5',
      format: 'BAM',
    },
  ],
  experiment_method_supporting_files: [],
  analysis_method_supporting_files: [],
  individual_supporting_files: [
    {
      accession: 'GHGAF12345678901239',
      ega_accession: 'EGAF12345678906',
      name: 'Supporting file 1',
      format: 'PDF',
    },
    {
      accession: 'GHGAF12345678901240',
      ega_accession: 'EGAF12345678907',
      name: 'Supporting file 2',
      format: 'PDF',
    },
  ],
  research_data_files: [
    {
      accession: 'GHGAF12345678901241',
      ega_accession: 'EGAF12345678908',
      name: 'Research data file 1',
      format: 'FASTQ',
    },
    {
      accession: 'GHGAF12345678901242',
      ega_accession: 'EGAF12345678909',
      name: 'Research data file 2',
      format: 'FASTQ',
    },
    {
      accession: 'GHGAF12345678901243',
      ega_accession: 'EGAF12345678910',
      name: 'Research data file 3',
      format: 'FASTQ',
    },
    {
      accession: 'GHGAF12345678901244',
      ega_accession: 'EGAF12345678911',
      name: 'Research data file 4',
      format: 'FASTQ',
    },
    {
      accession: 'GHGAF12345678901245',
      ega_accession: 'EGAF12345678912',
      name: 'Research data file 5',
      format: 'FASTQ',
    },
  ],
  experiments: [
    {
      accession: 'GHGAE12345678901234',
      ega_accession: 'EGAE12345678901',
      title: 'Text Experiment 1',
      description:
        'Test Experiment 1. Sagittis purus sit amet volutpat. Tellus cras adipiscing enim eu turpis egestas pretium. Vitae suscipit tellus mauris a diam maecenas sed enim ut. Vulputate enim nulla aliquet porttitor lacus luctus. Egestas sed sed risus pretium quam vulputate dignissim. Netus et malesuada fames ac turpis egestas maecenas. Nisl condimentum id venenatis a condimentum vitae sapien. Commodo quis imperdiet massa tincidunt nunc pulvinar sapien et. Vitae sapien pellentesque habitant morbi tristique senectus. Leo vel fringilla est ullamcorper eget nulla. Tempus egestas sed sed risus.',
      experiment_method: 'GHGAEM12345678901234',
    },
    {
      accession: 'GHGAE12345678901235',
      ega_accession: 'EGAE12345678902',
      title: 'Text Experiment 2',
      description: 'Test Experiment 2. Sagittis purus sit amet volutpat.',
      experiment_method: 'GHGAEM12345678901235',
    },
  ],
  experiment_methods: [
    {
      accession: 'GHGAEM12345678901234',
      name: 'DNA-Seq',
      type: 'Experiment Method 1',
      instrument_model: 'Experiment Platform 1',
    },
    {
      accession: 'GHGAEM12345678901235',
      name: 'RNA-Seq',
      type: 'Experiment Method 2',
      instrument_model: 'Experiment Platform 2',
    },
  ],
  individuals: [
    {
      accession: 'GHGAI12345678901234',
      sex: 'FEMALE',
      phenotypic_features_terms: [
        'Test phenotypic feature 1',
        'Lorem ipsum dolor sit amet consectetur adipiscing elit',
      ],
    },
    {
      accession: 'GHGAI12345678901235',
      sex: 'MALE',
      phenotypic_features_terms: [
        'Test phenotypic feature 2 Lorem ipsum dolor sit amet consectetur adipiscing elit',
      ],
    },
    {
      accession: 'GHGAI12345678901236',
      phenotypic_features_terms: [
        'Test phenotypic feature 3 Lorem ipsum dolor sit amet consectetur adipiscing elit',
      ],
      sex: 'FEMALE',
    },
  ],
  samples: [
    {
      accession: 'GHGAN12345678901234',
      ega_accession: 'EGAN12345678903',
      description:
        'Test Sample 1. Vivamus arcu felis bibendum ut. Eget mi proin sed libero enim. Metus dictum at tempor commodo ullamcorper a lacus. Tincidunt tortor aliquam nulla facilisi cras. Nullam vehicula ipsum a arcu. Malesuada proin libero nunc consequat. Purus faucibus ornare suspendisse sed nisi lacus sed viverra tellus. Elementum eu facilisis sed odio morbi quis. Condimentum id venenatis a condimentum vitae sapien pellentesque habitant. Purus sit amet volutpat consequat mauris nunc. Ultricies mi quis hendrerit dolor magna eget est lorem. Fermentum leo vel orci porta non pulvinar. Integer malesuada nunc vel risus commodo viverra maecenas.',
      name: 'Test anatomical entity',
      case_control_status: 'Test control status',
      individual: 'GHGAI12345678901234',
      biospecimen_type: 'Test biospecimen type 1',
      biospecimen_tissue_term: 'Test tissue',
    },
    {
      accession: 'GHGAN12345678901235',
      ega_accession: 'EGAN12345678904',
      description: 'Test Sample 2. Vivamus arcu felis bibendum ut.',
      name: 'Test anatomical entity 2',
      case_control_status: 'Test control status 2',
      individual: 'GHGAI12345678901235',
      biospecimen_type: 'Test biospecimen type 2',
      biospecimen_tissue_term: 'Test tissue 2',
    },
    {
      accession: 'GHGAN12345678901236',
      ega_accession: 'EGAN12345678905',
      description: 'Test Sample 3. Vivamus arcu felis bibendum ut.',
      name: 'Test anatomical entity 3',
      case_control_status: 'Test control status 3',
      individual: 'GHGAI12345678901236',
      biospecimen_type: 'Test biospecimen type 3',
      biospecimen_tissue_term: 'Test tissue 3',
    },
  ],
};

/**
 * MASS API
 */

export const searchResults: SearchResults = {
  facets: [
    {
      key: 'studies.type',
      name: 'Study Type',
      options: [
        { value: 'Option 1', count: 62 },
        { value: 'Option 2', count: 37 },
        { value: 'Option 3', count: 42 },
        { value: 'Option 4', count: 21 },
        { value: 'Option 5', count: 9 },
        { value: 'Option 6', count: 78 },
        { value: 'Option 7', count: 6 },
        { value: 'Option 8', count: 12 },
      ],
    },
    {
      key: 'type',
      name: 'Dataset Type with a test for how the UI handles facet names that span more than two lines in the expansion panel headers. So long, and thanks for all the fish.',
      options: [
        {
          value:
            'Test dataset lorem ipsum dolor sit amet, consectetur adipiscing elit. Ut eget neque non enim sagittis sollicitudin.',
          count: 12,
        },
        { value: 'Test dataset type 2', count: 87 },
      ],
    },
  ],
  count: 26, // just to test the paginator
  hits: [
    {
      id_: 'GHGAD12345678901234',
      content: {
        ega_accession: 'EGAD12345678901',
        title:
          'Test dataset for details and this is also testing whether two lines of text actually appear correctly on the expansion panel headers or not at least at a resolution of one thousand nine hundred and twenty pixels wide',
      },
    },
    {
      id_: 'GHGAD12345678901235',
      content: {
        ega_accession: 'EGAD12345678902',
        title: 'Test dataset for details',
      },
    },
    {
      id_: 'GHGAD12345678901236',
      content: {
        ega_accession: 'EGAD12345678903',
        title:
          'Test dataset for details and this is also testing whether more than two lines of text actually appear correctly on the expansion panel headers or not at least at a resolution of one thousand nine hundred and twenty pixels wide especially since this can cause issues with the layout of the expansion panels',
      },
    },
    {
      id_: 'GHGAD12345678901237',
      content: {
        ega_accession: '   ',
        title:
          'Test dataset for details and this is also testing whether two lines of text actually appear correctly on the expansion panel headers or not at least at a resolution of one thousand nine hundred and twenty pixels wide',
      },
    },

    {
      id_: 'GHGAD12345678901238',
      content: {
        title:
          'Test dataset for details and this is also testing whether two lines of text actually appear correctly on the expansion panel headers or not at least at a resolution of one thousand nine hundred and twenty pixels wide',
      },
    },
    {
      id_: 'GHGAD99999999999001',
      content: {
        ega_accession: 'EGAD99999999001',
        title: 'Upload Box Test Dataset',
      },
    },
  ],
};

/**
 * ARS API
 */
const startDate = new Date();
const endDate = new Date(startDate);
endDate.setFullYear(endDate.getFullYear() + 1);
const access_starts = startDate.toISOString();
const access_ends = endDate.toISOString();

let dateYesterday = new Date();
dateYesterday.setDate(dateYesterday.getDate() - 1);

let dateOneYearAgo = new Date();
dateOneYearAgo.setDate(dateOneYearAgo.getDate() - 365);

export const accessRequests = [
  {
    id: '62bcc452-a70b-47c1-9870-55da40d8e45f',
    user_id: 'doe@test.dev',
    dataset_id: 'GHGAD12345678901234',
    dataset_title: 'Test dataset for details',
    dac_alias: 'Data Access Committee of Heidelberg Center for Rare Diseases',
    dac_email: 'info@dac.com',
    full_user_name: 'Dr. John Doe',
    email: 'doe@home.org',
    request_text:
      'This is a test request for dataset GHGAD12345678901234. Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.',
    access_starts: access_starts,
    access_ends: access_ends,
    request_created: '2023-05-09T12:04:02.000Z',
    status: 'denied',
    status_changed: null,
    changed_by: null,
    internal_note: null,
    note_to_requester: null,
    ticket_id: null,
  },
  {
    id: '4ef4ccac-6c0a-4be6-9637-b33925178cea',
    user_id: 'doe@test.dev',
    dataset_id: 'GHGAD12345678901235',
    dac_alias: 'Data Access Committee of Heidelberg Center for Personalized Oncology',
    dac_email: 'info@dac.com',
    dataset_title: 'Test dataset for details',
    full_user_name: 'Dr. John Doe',
    email: 'j.jdoe@home.org',
    request_text: 'This is a test request for dataset GHGAD12345678901235.',
    access_starts: access_starts,
    access_ends: access_ends,
    request_created: '2023-05-11T12:04:02.000Z',
    status: 'allowed',
    status_changed: '2023-05-19T12:04:03.000Z',
    changed_by: 'doe@test.dev',
    iva_id: 'fc3c0ad8-01a4-4eb1-b8f3-40b04bb4bcb2',
    internal_note: 'An internal note for the request.',
    note_to_requester: 'This is a note to the requester.',
    ticket_id: null,
  },
  {
    id: '4ef4ccac-6c0a-4be6-9637-b339251793fb',
    user_id: 'doe@test.dev',
    dataset_id: 'GHGAD12345678901235',
    dac_alias: 'Data Access Committee of Heidelberg Center for Personalized Oncology',
    dac_email: 'info@dac.com',
    dataset_title: 'Test dataset for details',
    full_user_name: 'Dr. John Doe',
    email: 'j.jdoe@home.org',
    request_text:
      'This is a test request for dataset GHGAD12345678901235. It is expired.',
    access_starts: dateOneYearAgo,
    access_ends: dateYesterday,
    request_created: '2023-05-11T12:04:02.000Z',
    status: 'allowed',
    status_changed: '2023-05-19T11:59:03.000Z',
    changed_by: 'doe@test.dev',
    iva_id: '783d9682-d5e5-4ce7-9157-9eeb53a1e9ba',
    internal_note: 'Allowed by Paul on 2023-05-19.',
    note_to_requester: null,
    ticket_id: null,
  },
  {
    id: 'a787d591-4264-4f48-8827-598585db868e',
    user_id: 'doe@test.dev',
    dataset_id: 'GHGAD12345678901236',
    dac_alias: 'Data Access Committee of Heidelberg Center for Personalized Oncology',
    dac_email: 'info@dac.com',
    dataset_title:
      'Test dataset for details and this is also testing whether more than two lines of text actually appear correctly on the expansion panel headers or not at least at a resolution of one thousand nine hundred and twenty pixels wide especially since this can cause issues with the layout of the expansion panels',
    full_user_name: 'Dr. John Doe',
    email: 'doe@home.org',
    request_text: 'This is a test request for dataset GHGAD12345678901236.',
    access_starts: access_starts,
    access_ends: access_ends,
    request_created: '2023-05-18T12:04:03.000Z',
    status: 'denied',
    status_changed: '2023-05-19T12:04:02.000Z',
    changed_by: 'doe@test.dev',
    internal_note: null,
    note_to_requester: null,
    ticket_id: 'GSI-1559',
  },
  {
    id: '9409db13-e23e-433e-9afa-544d8f25b720',
    user_id: 'doe@test.dev',
    dataset_id: 'GHGAD12345678901235',
    dac_alias: 'Data Access Committee of Heidelberg Center for Personalized Oncology',
    dac_email: 'info@dac.com',
    dataset_title: 'Test dataset for details',
    full_user_name: 'Dr. John Doe',
    email: 'doe@home.org',
    request_text: 'This is a test request for dataset GHGAD12345678901236.',
    access_starts: access_starts,
    access_ends: access_ends,
    request_created: '2023-05-18T12:04:03.000Z',
    status: 'pending',
    status_changed: '2023-05-19T12:04:02.000Z',
    changed_by: 'doe@test.dev',
    internal_note: 'We need to ask X about this.',
    note_to_requester: 'Please wait for the approval. Additional steps were required.',
    ticket_id: '1582',
  },

  {
    id: '3823d3f7-da5d-4dcb-afd2-d45de96c8cba',
    user_id: 'mar@test.dev',
    dataset_id: 'GHGAD12345678901234',
    dac_alias: 'Data Access Committee of Heidelberg Center for Personalized Oncology',
    dac_email: 'info@dac.com',
    dataset_title: 'Test dataset for details',
    full_user_name: 'Dr. Joan Mar',
    email: 'mar@home.org',
    request_text: 'This is a test request for dataset GHGAD12345678901234.',
    access_starts: access_starts,
    access_ends: access_ends,
    request_created: '2025-05-18T12:04:03.000Z',
    status: 'pending',
    status_changed: '2025-05-19T12:04:02.000Z',
    changed_by: 'mar@test.dev',
    internal_note: 'We need to ask X about this.',
    note_to_requester: 'Please wait for the approval. Additional steps were required.',
    ticket_id: '1138',
  },
];

export const accessGrants: AccessGrant[] = [
  {
    id: 'grant-ghga-8c4b9d5a1f0a',
    user_id: 'doe@test.dev',
    dataset_id: 'GHGAD12345678901234',
    created: '2025-07-20T10:00:00Z',
    valid_from: '2025-08-01T00:00:00Z',
    valid_until: '2026-08-01T00:00:00Z',
    user_name: 'John Doe',
    user_title: 'Dr.',
    user_email: 'doe@home.org',
    dataset_title: 'Test dataset 1 ready for download',
    dac_alias: 'SOME-DAC',
    dac_email: 'dac-main@some.org',
    iva_id: '783d9682-d5e5-4ce7-9157-9eeb53a1e9ba',
  },
  {
    id: 'grant-ghga-8c4b9d5a1f0b',
    user_id: 'doe@test.dev',
    dataset_id: 'GHGAD12345678901235',
    created: '2025-07-20T10:00:00Z',
    valid_from: '2025-08-01T00:00:00Z',
    valid_until: '2026-08-01T00:00:00Z',
    user_name: 'John Doe',
    user_title: 'Dr.',
    user_email: 'doe@home.org',
    dataset_title: 'Test dataset 2 with an unverified IVA',
    dac_alias: 'SOME-DAC',
    dac_email: 'dac-main@some.org',
    iva_id: 'fc3c0ad8-01a4-4eb1-b8f3-40b04bb4bcb2',
  },
  {
    id: 'grant-ghga-8c4b9d5a1f0c',
    user_id: 'doe@test.dev',
    dataset_id: 'GHGAD12345678901236',
    created: '2025-07-20T10:00:00Z',
    valid_from: '2025-08-01T00:00:00Z',
    valid_until: '2026-08-01T00:00:00Z',
    user_name: 'John Doe',
    user_title: 'Dr.',
    user_email: 'doe@home.org',
    dataset_title:
      'Test dataset 3 for download with a long title and a broken IVA which should never happen',
    dac_alias: 'SOME-DAC',
    dac_email: 'dac-main@some.org',
    iva_id: '347368b5-718e-49ba-80ad-bc128e83b609',
  },
  {
    id: 'grant-ghga-8c4b9d5a1f0d',
    user_id: 'doe@test.dev',
    dataset_id: 'GHGAD12345678901237',
    created: '2023-05-19T12:00:00Z',
    valid_from: '2025-01-05T00:00:00Z',
    valid_until: '2025-01-10T00:00:00Z',
    user_name: 'John Doe',
    user_title: 'Dr.',
    user_email: 'doe@home.org',
    dataset_title: 'Test dataset 4 for download',
    dac_alias: 'SOME-DAC',
    dac_email: 'dac-main@some.org',
    iva_id: '32b50c92-489f-4418-ace8-e7552e3cf36d',
  },
  {
    id: 'grant-ghga-8c4b9d5a1f0e',
    user_id: 'roe@test.dev',
    dataset_id: 'GHGAD12345678901234',
    created: '2025-07-20T10:00:00Z',
    valid_from: '2027-08-01T00:00:00Z',
    valid_until: '2028-08-01T00:00:00Z',
    user_name: 'Jane Doe',
    user_title: 'Prof.',
    user_email: 'roe@home.org',
    dataset_title: 'Test dataset 1 for download',
    dac_alias: 'SOME-DAC',
    dac_email: 'dac-main@some.org',
    iva_id: '0063effb-2c43-4948-ba6f-f15425cb72d7',
  },
];

export const getAccessRequests = (user_id?: string, dataset_id?: string) =>
  accessRequests.filter(
    (x) =>
      (!dataset_id || x.dataset_id === dataset_id) &&
      (!user_id || x.user_id === user_id),
  );

export const getAccessGrants = (user_id?: string) =>
  accessGrants.filter((x) => !user_id || x.user_id === user_id);

/**
 * DINS API
 */

export const datasetInformation: DatasetInformation = {
  accession: 'GHGAD12345678901234',
  file_information: [
    {
      accession: 'GHGAF12345678901234',
      sha256_hash: '58b2e5a09936322db4ab1b921847d0f3b83027e0255cd24d7e58c420845286d1',
      size: 1234567891,
      storage_alias: 'TUE01',
    },
    {
      accession: 'GHGAF12345678901235',
      sha256_hash: '58b2e5a09936322db4ab1b921847d0f3b83027e0255cd24d7e58c420845286d2',
      size: 1234567892,
      storage_alias: 'TUE02',
    },
    {
      accession: 'GHGAF12345678901236',
      sha256_hash: '58b2e5a09936322db4ab1b921847d0f3b83027e0255cd24d7e58c420845286d3',
      size: 1234567893,
      storage_alias: 'TUE03',
    },
    {
      accession: 'GHGAF12345678901237',
      sha256_hash: '58b2e5a09936322db4ab1b921847d0f3b83027e0255cd24d7e58c420845286d4',
      size: 1234567894,
      storage_alias: 'TUE04',
    },
    {
      accession: 'GHGAF12345678901238',
      sha256_hash: '58b2e5a09936322db4ab1b921847d0f3b83027e0255cd24d7e58c420845286d5',
      size: 1234567895,
      storage_alias: 'TUE05',
    },
    {
      accession: 'GHGAF12345678901241',
      sha256_hash: '47b2e5a09936322db4ab1b921847d0f3b83027e0255cd24d7e58c420845286e1',
      size: 87654321,
      storage_alias: 'HD01',
    },
    {
      accession: 'GHGAF12345678901242',
      sha256_hash: '47b2e5a09936322db4ab1b921847d0f3b83027e0255cd24d7e58c420845286e2',
      size: 87654322,
      storage_alias: 'HD02',
    },
    {
      accession: 'GHGAF12345678901243',
      sha256_hash: '47b2e5a09936322db4ab1b921847d0f3b83027e0255cd24d7e58c420845286e3',
      size: 87654323,
      storage_alias: 'HD03',
    },
    {
      accession: 'GHGAF12345678901244',
      sha256_hash: '47b2e5a09936322db4ab1b921847d0f3b83027e0255cd24d7e58c420845286e4',
      size: 87654324,
      storage_alias: 'HD04',
    },
    {
      accession: 'GHGAF12345678901245',
      sha256_hash: '47b2e5a09936322db4ab1b921847d0f3b83027e0255cd24d7e58c420845286e5',
      size: 87654325,
      storage_alias: 'HD05',
    },
  ],
};

/**
 * RS Boxes API
 */

export const uploadBoxes: BoxRetrievalResults = {
  count: 3,
  boxes: [
    {
      id: '0a36607a-b53f-49ed-bf3e-a5f2dbc68001',
      version: 1,
      state: UploadBoxState.open,
      title: 'Research Data Upload Box of John',
      description: 'Upload box for RNA sequencing files of study GHGAS12345678901234',
      last_changed: '2025-02-01T09:00:00Z',
      changed_by: 'doe@test.dev',
      file_count: 3,
      size: 123456789,
      storage_alias: 'TUE01',
    },
    {
      id: '0a36607a-b53f-49ed-bf3e-a5f2dbc68002',
      version: 4,
      state: UploadBoxState.locked,
      title: 'Research Data Upload Box of Jane',
      description: 'Upload box pending data steward review before archival handover',
      last_changed: '2025-02-02T10:00:00Z',
      changed_by: 'roe@test.dev',
      file_count: 15,
      size: 120259084288, // ~112 GB total
      storage_alias: 'HD02',
    },
    {
      id: '0a36607a-b53f-49ed-bf3e-a5f2dbc68003',
      version: 2,
      state: UploadBoxState.archived,
      title: 'Research Data Upload Box of Joan',
      description: 'Archived upload box with finalized metadata and checksum review',
      last_changed: '2025-02-03T11:00:00Z',
      changed_by: 'mar@test.dev',
      file_count: 28,
      size: 1567890123,
      storage_alias: 'TUE03',
    },
  ],
};

/**
 * RS Grants API
 */
export const uploadGrants: GrantWithBoxInfo[] = [
  {
    id: 'grant-rs-001',
    user_id: 'doe@test.dev',
    iva_id: '783d9682-d5e5-4ce7-9157-9eeb53a1e9ba',
    box_id: '0a36607a-b53f-49ed-bf3e-a5f2dbc68001',
    created: '2026-01-01T00:00:00Z',
    valid_from: '2026-01-01',
    valid_until: '2026-12-31',
    user_name: 'John Doe',
    user_email: 'doe@home.org',
    user_title: 'Dr.',
    box_title: 'Research Data Upload Box of John',
    box_description: 'Upload box for RNA sequencing files of study GHGAS12345678901234',
    box_state: UploadBoxState.open,
    box_version: 1,
  },
  {
    id: 'grant-rs-002',
    user_id: 'doe@test.dev',
    iva_id: '32b50c92-489f-4418-ace8-e7552e3cf36d',
    box_id: '0a36607a-b53f-49ed-bf3e-a5f2dbc68002',
    created: '2026-01-03T00:00:00Z',
    valid_from: '2026-01-03',
    valid_until: '2026-12-31',
    user_name: 'John Doe',
    user_email: 'doe@home.org',
    user_title: 'Dr.',
    box_title: 'Research Data Upload Box 2 of John',
    box_description: 'Upload box for proteomics files of study GHGAS12345678901235',
    box_state: UploadBoxState.open,
    box_version: 4,
  },
  {
    id: 'grant-rs-003',
    user_id: 'doe@test.dev',
    iva_id: null,
    box_id: '0a36607a-b53f-49ed-bf3e-a5f2dbc68003',
    created: '2026-01-05T00:00:00Z',
    valid_from: '2026-01-05',
    valid_until: '2026-12-31',
    user_name: 'John Doe',
    user_email: 'doe@home.org',
    user_title: 'Dr.',
    box_title: 'Research Data Upload Box 3 of John',
    box_description: 'Upload box for imaging files of study GHGAS12345678901236',
    box_state: UploadBoxState.open,
    box_version: 2,
  },
];

/**
 * RS file uploads for box 1 (open, 3 files)
 */
export const uploadBox1FileUploads: FileUploadWithAccession[] = [
  {
    id: 'f1b36607a-b53f-49ed-bf3e-a5f2dbc68001',
    box_id: '0a36607a-b53f-49ed-bf3e-a5f2dbc68001',
    alias: 'sample_rna_001_R1.fastq.gz',
    state: 'interrogated',
    state_updated: '2026-01-10T08:00:00Z',
    storage_alias: 'TUE01',
    bucket_id: 'inbox-tue01',
    decrypted_sha256: 'a'.repeat(64),
    decrypted_size: 5368709120, // 5 GB
    encrypted_size: 5368750000,
    part_size: 16777216,
    accession: null,
  },
  {
    id: 'f2b36607a-b53f-49ed-bf3e-a5f2dbc68001',
    box_id: '0a36607a-b53f-49ed-bf3e-a5f2dbc68001',
    alias: 'sample_rna_001_R2.fastq.gz',
    state: 'interrogated',
    state_updated: '2026-01-10T08:05:00Z',
    storage_alias: 'TUE01',
    bucket_id: 'inbox-tue01',
    decrypted_sha256: 'b'.repeat(64),
    decrypted_size: 5100273664, // ~4.75 GB
    encrypted_size: 5100310000,
    part_size: 16777216,
    accession: null,
  },
  {
    id: 'f3b36607a-b53f-49ed-bf3e-a5f2dbc68001',
    box_id: '0a36607a-b53f-49ed-bf3e-a5f2dbc68001',
    alias: 'metadata_manifest.csv',
    state: 'inbox',
    state_updated: '2026-01-10T09:00:00Z',
    storage_alias: 'TUE01',
    bucket_id: 'inbox-tue01',
    decrypted_sha256: null,
    decrypted_size: 0,
    encrypted_size: 0,
    part_size: 16777216,
    accession: null,
  },
];

/**
 * RS file uploads for box 2 (locked, 15 files)
 */
export const uploadBox2FileUploads: FileUploadWithAccession[] = [
  {
    id: 'f1a36607a-b53f-49ed-bf3e-a5f2dbc68001',
    box_id: '0a36607a-b53f-49ed-bf3e-a5f2dbc68002',
    alias: 'sample_001_R1.fastq',
    state: 'interrogated',
    state_updated: '2026-01-14T10:12:00Z',
    storage_alias: 'HD02',
    bucket_id: 'inbox-hd02',
    decrypted_sha256: 'a'.repeat(64),
    decrypted_size: 12884901888, // 12 GB
    encrypted_size: 12884950000,
    part_size: 16777216,
    accession: null,
  },
  {
    id: 'f2a36607a-b53f-49ed-bf3e-a5f2dbc68002',
    box_id: '0a36607a-b53f-49ed-bf3e-a5f2dbc68002',
    alias: 'sample_001_R2.fastq',
    state: 'interrogated',
    state_updated: '2026-01-14T10:45:00Z',
    storage_alias: 'HD02',
    bucket_id: 'inbox-hd02',
    decrypted_sha256: 'b'.repeat(64),
    decrypted_size: 12991488000, // ~12.1 GB
    encrypted_size: 12991530000,
    part_size: 16777216,
    accession: null,
  },
  {
    id: 'f3a36607a-b53f-49ed-bf3e-a5f2dbc68003',
    box_id: '0a36607a-b53f-49ed-bf3e-a5f2dbc68002',
    alias: 'sample_002_R1.fastq.gz',
    state: 'interrogated',
    state_updated: '2026-01-14T11:20:00Z',
    storage_alias: 'HD02',
    bucket_id: 'inbox-hd02',
    decrypted_sha256: 'c'.repeat(64),
    decrypted_size: 4831838208, // ~4.5 GB
    encrypted_size: 4831880000,
    part_size: 16777216,
    accession: null,
  },
  {
    id: 'f4a36607a-b53f-49ed-bf3e-a5f2dbc68004',
    box_id: '0a36607a-b53f-49ed-bf3e-a5f2dbc68002',
    alias: 'sample_002_R2.fastq.gz',
    state: 'interrogated',
    state_updated: '2026-01-14T11:55:00Z',
    storage_alias: 'HD02',
    bucket_id: 'inbox-hd02',
    decrypted_sha256: 'd'.repeat(64),
    decrypted_size: 4724464640, // ~4.4 GB
    encrypted_size: 4724500000,
    part_size: 16777216,
    accession: null,
  },
  {
    id: 'f5a36607a-b53f-49ed-bf3e-a5f2dbc68005',
    box_id: '0a36607a-b53f-49ed-bf3e-a5f2dbc68002',
    alias: 'reference_genome.fasta',
    state: 'interrogated',
    state_updated: '2026-01-15T08:30:00Z',
    storage_alias: 'HD02',
    bucket_id: 'inbox-hd02',
    decrypted_sha256: 'e'.repeat(64),
    decrypted_size: 3221225472, // 3 GB
    encrypted_size: 3221260000,
    part_size: 16777216,
    accession: null,
  },
  {
    id: 'f6a36607a-b53f-49ed-bf3e-a5f2dbc68006',
    box_id: '0a36607a-b53f-49ed-bf3e-a5f2dbc68002',
    alias: 'aligned_reads_001.bam',
    state: 'interrogated',
    state_updated: '2026-01-15T09:10:00Z',
    storage_alias: 'HD02',
    bucket_id: 'inbox-hd02',
    decrypted_sha256: 'f'.repeat(64),
    decrypted_size: 31138512896, // 29 GB
    encrypted_size: 31138550000,
    part_size: 16777216,
    accession: null,
  },
  {
    id: 'f7a36607a-b53f-49ed-bf3e-a5f2dbc68007',
    box_id: '0a36607a-b53f-49ed-bf3e-a5f2dbc68002',
    alias: 'aligned_reads_002.cram',
    state: 'interrogated',
    state_updated: '2026-01-15T09:55:00Z',
    storage_alias: 'HD02',
    bucket_id: 'inbox-hd02',
    decrypted_sha256: '1'.repeat(64),
    decrypted_size: 8053063680, // 7.5 GB
    encrypted_size: 8053100000,
    part_size: 16777216,
    accession: null,
  },
  {
    id: 'f8a36607a-b53f-49ed-bf3e-a5f2dbc68008',
    box_id: '0a36607a-b53f-49ed-bf3e-a5f2dbc68002',
    alias: 'variants_cohort.vcf',
    state: 'interrogated',
    state_updated: '2026-01-15T14:00:00Z',
    storage_alias: 'HD02',
    bucket_id: 'inbox-hd02',
    decrypted_sha256: '2'.repeat(64),
    decrypted_size: 524288000, // 500 MB
    encrypted_size: 524310000,
    part_size: 16777216,
    accession: null,
  },
  {
    id: 'f9a36607a-b53f-49ed-bf3e-a5f2dbc68009',
    box_id: '0a36607a-b53f-49ed-bf3e-a5f2dbc68002',
    alias: 'chip_peaks_001.bed',
    state: 'interrogated',
    state_updated: '2026-01-15T14:30:00Z',
    storage_alias: 'HD02',
    bucket_id: 'inbox-hd02',
    decrypted_sha256: '3'.repeat(64),
    decrypted_size: 10485760, // 10 MB
    encrypted_size: 10486000,
    part_size: 16777216,
    accession: null,
  },
  {
    id: 'fa036607a-b53f-49ed-bf3e-a5f2dbc68010',
    box_id: '0a36607a-b53f-49ed-bf3e-a5f2dbc68002',
    alias: 'methylation_sample_001.meth',
    state: 'interrogated',
    state_updated: '2026-01-16T08:00:00Z',
    storage_alias: 'HD02',
    bucket_id: 'inbox-hd02',
    decrypted_sha256: '4'.repeat(64),
    decrypted_size: 2147483648, // 2 GB
    encrypted_size: 2147520000,
    part_size: 16777216,
    accession: null,
  },
  {
    id: 'fb036607a-b53f-49ed-bf3e-a5f2dbc68011',
    box_id: '0a36607a-b53f-49ed-bf3e-a5f2dbc68002',
    alias: 'ms_proteomics_run1.raw',
    state: 'interrogated',
    state_updated: '2026-01-16T09:15:00Z',
    storage_alias: 'HD02',
    bucket_id: 'inbox-hd02',
    decrypted_sha256: '5'.repeat(64),
    decrypted_size: 1610612736, // 1.5 GB
    encrypted_size: 1610650000,
    part_size: 16777216,
    accession: null,
  },
  {
    id: 'fc036607a-b53f-49ed-bf3e-a5f2dbc68012',
    box_id: '0a36607a-b53f-49ed-bf3e-a5f2dbc68002',
    alias: 'study_data_manifest.pdf',
    state: 'interrogated',
    state_updated: '2026-01-16T10:00:00Z',
    storage_alias: 'HD02',
    bucket_id: 'inbox-hd02',
    decrypted_sha256: '6'.repeat(64),
    decrypted_size: 2097152, // 2 MB
    encrypted_size: 2097200,
    part_size: 16777216,
    accession: null,
  },
  {
    id: 'fd036607a-b53f-49ed-bf3e-a5f2dbc68013',
    box_id: '0a36607a-b53f-49ed-bf3e-a5f2dbc68002',
    alias: 'sample_003_R1.fastq.gz',
    state: 'failed',
    state_updated: '2026-01-16T11:00:00Z',
    storage_alias: 'HD02',
    bucket_id: 'inbox-hd02',
    decrypted_sha256: null,
    decrypted_size: 0,
    encrypted_size: 0,
    part_size: 16777216,
    accession: null,
  },
  {
    id: 'fe036607a-b53f-49ed-bf3e-a5f2dbc68014',
    box_id: '0a36607a-b53f-49ed-bf3e-a5f2dbc68002',
    alias: 'aligned_reads_003.bam',
    state: 'awaiting_archival',
    state_updated: '2026-01-17T07:45:00Z',
    storage_alias: 'HD02',
    bucket_id: 'inbox-hd02',
    decrypted_sha256: '7'.repeat(64),
    decrypted_size: 42949672960, // 40 GB
    encrypted_size: 42949720000,
    part_size: 16777216,
    accession: null,
  },
  {
    id: 'ff036607a-b53f-49ed-bf3e-a5f2dbc68015',
    box_id: '0a36607a-b53f-49ed-bf3e-a5f2dbc68002',
    alias: 'chip_peaks_002.bed',
    state: 'interrogated',
    state_updated: '2026-01-17T08:30:00Z',
    storage_alias: 'HD02',
    bucket_id: 'inbox-hd02',
    decrypted_sha256: '8'.repeat(64),
    decrypted_size: 15728640, // 15 MB
    encrypted_size: 15729000,
    part_size: 16777216,
    accession: null,
  },
];

/**
 * RS file uploads for box 3 (archived, 28 files)
 */
export const uploadBox3FileUploads: FileUploadWithAccession[] = Array.from(
  { length: 28 },
  (_, i) => ({
    id: `f${String(i + 1).padStart(2, '0')}036607a-b53f-49ed-bf3e-a5f2dbc68003`,
    box_id: '0a36607a-b53f-49ed-bf3e-a5f2dbc68003',
    alias: `archived_sample_${String(i + 1).padStart(3, '0')}.fastq.gz`,
    state: 'archived' as FileUploadWithAccession['state'],
    state_updated: '2025-06-01T10:00:00Z',
    storage_alias: 'TUE03',
    bucket_id: 'inbox-tue03',
    decrypted_sha256: (i % 10).toString().repeat(64),
    decrypted_size: (i + 1) * 536870912, // 0.5–14 GB per file
    encrypted_size: (i + 1) * 536870912 + 48000,
    part_size: 16777216,
    accession: `GHGAF1234567890${String(2200 + i).padStart(4, '0')}`,
  }),
);

/**
 * WPS API
 */

export const datasets: DatasetWithExpiration[] = [
  {
    id: 'GHGAD12345678901234',
    title: 'Some dataset to download',
    description:
      'This is a very interesting dataset that can be used' +
      ' to test the download functionality of the Data Portal.' +
      ' Note that the description can be longer than the title.',
    stage: 'download',
    files: [
      { extension: 'txt', id: 'GHGAF12345678901234' },
      { extension: 'csv', id: 'GHGAF12345678901235' },
      { extension: 'pdf', id: 'GHGAF12345678901236' },
    ],
    expires: access_ends,
  },
  {
    id: 'GHGAD12345678901235',
    title: 'Another dataset to download',
    description:
      'This is a very interesting dataset that can be used' +
      ' to test the download functionality of the Data Portal.' +
      ' Note that the description can be longer than the title.',
    stage: 'download',
    files: [],
    expires: access_ends,
  },
  {
    id: 'GHGAD12345678901236',
    title: 'A third dataset to download',
    description:
      'This is another todally ineresting dataset that can be used' +
      ' to test the download functionality of the Data Portal.' +
      ' Note that the description can be longer than the title.',
    stage: 'download',
    files: [],
    expires: access_ends,
  },
  {
    id: 'GHGAD12345678901237',
    title: 'A fourth dataset to download',
    description:
      'This is another todally ineresting dataset that can be used' +
      ' to test the download functionality of the Data Portal.' +
      ' Note that the description can be longer than the title.',
    stage: 'download',
    files: [],
    expires: access_ends,
  },
  {
    id: 'GHGAD12345678901238',
    title: 'A fifth dataset to download',
    description:
      'This is another todally ineresting dataset that can be used' +
      ' to test the download functionality of the Data Portal.' +
      ' Note that the description can be longer than the title.',
    stage: 'download',
    files: [],
    expires: access_ends,
  },
];

export const workPackageResponse: WorkPackageResponse = {
  id: '7f562eb5-a0a5-427d-b40f-f91198d27309',
  // the encrypted work package token (which can be pretty long)
  token:
    'gumRa5XE1Rm3tOJr3ocfA1F63rRUI2g6eCI0KY2Mv3epb28cZeylvaYsxRmgQRDboE2yOhtE4qxPhZgYz/Y7zR+hssBzq7Hg',
  expires: '2026-01-01T12:00:00',
};

export const storageLabels: BaseStorageLabels = {
  storage_labels: {
    TUE01: 'Tübingen 1',
    TUE02: 'Tübingen 2',
    TUE03: 'Tübingen 3',
    TUE04: 'Tübingen 4',
    TUE05: 'Tübingen 5',
    HD01: 'Heidelberg 1',
    HD02: 'Heidelberg 2',
    HD03: 'Heidelberg 3',
    HD04: 'Heidelberg 4',
    HD05: 'Heidelberg 5',
  },
};

export const studyData: Study = {
  accession: 'GHGAS12345678901234',
  ega_accession: 'EGAS12345678901',
  alias: 'TEST_STUDY',
  types: ['test_genomics_Lorem ipsum dolor sit amet, consectetur adipiscing elit'],
  title: 'Test Study',
  affiliations: ['Test affiliation'],
  datasets: ['GHGAD12345678901234', 'GHGAD12345678901235'],
  description:
    'Test study description. Pharetra convallis posuere morbi leo urna molestie. Ut faucibus pulvinar elementum integer. Nec nam aliquam sem et tortor. Pretium viverra suspendisse potenti nullam ac. Commodo sed egestas egestas fringilla. Tincidunt dui ut ornare lectus sit. Amet massa vitae tortor condimentum lacinia quis vel eros donec. Feugiat pretium nibh ipsum consequat. Pulvinar etiam non quam lacus suspendisse faucibus interdum. Aliquam sem et tortor consequat id.',
  publications: ['GHGA123456789', 'GHGA123456709'],
};

/**
 * Mock study for testing the upload box file mapping feature (box 2).
 * Files in `uploadBoxTestDatasetDetails.research_data_files` deliberately
 * cover exact alias matches, case-insensitive alias matches, exact name
 * matches, and un-matched files so all mapping branches can be exercised.
 */
export const uploadBoxTestStudyData: Study = {
  accession: 'GHGAS99999999999001',
  ega_accession: 'EGAS99999999901',
  alias: 'UPLOAD_BOX_TEST_STUDY',
  types: ['test_genomics'],
  title: 'Upload Box File Mapping Test Study',
  affiliations: ['Test affiliation'],
  datasets: ['GHGAD99999999999001'],
  description: 'Dedicated study for testing the file mapping UI with upload box 2.',
  publications: [],
};

/**
 * Minimal DatasetSummary for the upload-box-mapping test dataset.
 * The `studies_summary.stats.accession` must point to `uploadBoxTestStudyData`.
 */
export const uploadBoxTestDatasetSummary: DatasetSummary = {
  accession: 'GHGAD99999999999001',
  description: 'Upload box test dataset',
  types: ['test_genomics'],
  title: 'Upload Box Test Dataset',
  dac_email: 'test@some.dac.org',
  samples_summary: {
    count: 1,
    stats: { sex: [], tissues: [], phenotypic_features: [] },
  },
  studies_summary: {
    count: 1,
    stats: {
      accession: ['GHGAS99999999999001'],
      title: ['Upload Box File Mapping Test Study'],
    },
  },
  experiments_summary: { count: 1, stats: { experiment_methods: [] } },
  files_summary: {
    count: 16,
    stats: {
      format: [
        { value: 'FASTQ', count: 5 },
        { value: 'BAM', count: 2 },
        { value: 'CRAM', count: 1 },
        { value: 'VCF', count: 1 },
        { value: 'BED', count: 2 },
        { value: 'FASTA', count: 1 },
        { value: 'METH', count: 1 },
        { value: 'RAW', count: 1 },
        { value: 'PDF', count: 1 },
        { value: 'CSV', count: 1 },
      ],
    },
  },
};

/**
 * DatasetDetailsRaw for the upload-box-mapping test dataset.
 * `research_data_files` aliases/names are chosen to test all mapping scenarios:
 * - exact alias match (files 1–3, 5, 7–9, 11–15)
 * - case-insensitive alias match (files 4, 6)
 * - exact name match only (file 10)
 */
export const uploadBoxTestDatasetDetails: DatasetDetailsRaw = {
  ...datasetDetails,
  accession: 'GHGAD99999999999001',
  ega_accession: 'EGAD99999999001',
  title: 'Upload Box Test Dataset',
  description: 'Dedicated dataset for testing the file mapping UI.',
  process_data_files: [],
  experiment_method_supporting_files: [],
  analysis_method_supporting_files: [],
  individual_supporting_files: [],
  experiments: [],
  samples: [],
  research_data_files: [
    // Exact alias matches:
    {
      accession: 'GHGAF99999999999001',
      ega_accession: 'EGAF99999901',
      alias: 'sample_001_R1.fastq',
      name: 'Sample 001 Read 1',
      format: 'FASTQ',
    },
    {
      accession: 'GHGAF99999999999002',
      ega_accession: 'EGAF99999902',
      alias: 'sample_001_R2.fastq',
      name: 'Sample 001 Read 2',
      format: 'FASTQ',
    },
    {
      accession: 'GHGAF99999999999003',
      ega_accession: 'EGAF99999903',
      alias: 'sample_002_R1.fastq.gz',
      name: 'Sample 002 Read 1',
      format: 'FASTQ',
    },
    {
      accession: 'GHGAF99999999999005',
      ega_accession: 'EGAF99999905',
      alias: 'reference_genome.fasta',
      name: 'Reference Genome',
      format: 'FASTA',
    },
    {
      accession: 'GHGAF99999999999007',
      ega_accession: 'EGAF99999907',
      alias: 'aligned_reads_002.cram',
      name: 'Aligned Reads 002',
      format: 'CRAM',
    },
    {
      accession: 'GHGAF99999999999008',
      ega_accession: 'EGAF99999908',
      alias: 'variants_cohort.vcf',
      name: 'Variants Cohort',
      format: 'VCF',
    },
    {
      accession: 'GHGAF99999999999009',
      ega_accession: 'EGAF99999909',
      alias: 'chip_peaks_001.bed',
      name: 'ChIP Peaks 001',
      format: 'BED',
    },
    // Case-insensitive alias matches (alias case differs, name = exact box alias):
    {
      accession: 'GHGAF99999999999004',
      ega_accession: 'EGAF99999904',
      alias: 'Sample_002_R2.fastq.gz',
      name: 'sample_002_R2.fastq.gz',
      format: 'FASTQ',
    },
    {
      accession: 'GHGAF99999999999006',
      ega_accession: 'EGAF99999906',
      alias: 'ALIGNED_READS_001.BAM',
      name: 'aligned_reads_001.bam',
      format: 'BAM',
    },
    // Exact name match only (alias does not match any box file):
    {
      accession: 'GHGAF99999999999010',
      ega_accession: 'EGAF99999910',
      alias: 'methylation_data.meth',
      name: 'methylation_sample_001.meth',
      format: 'METH',
    },
    // Further exact alias matches:
    {
      accession: 'GHGAF99999999999011',
      ega_accession: 'EGAF99999911',
      alias: 'ms_proteomics_run1.raw',
      name: 'MS Proteomics Run 1',
      format: 'RAW',
    },
    {
      accession: 'GHGAF99999999999012',
      ega_accession: 'EGAF99999912',
      alias: 'study_data_manifest.pdf',
      name: 'Study Data Manifest',
      format: 'PDF',
    },
    {
      accession: 'GHGAF99999999999013',
      ega_accession: 'EGAF99999913',
      alias: 'sample_003_R1.fastq.gz',
      name: 'Sample 003 Read 1',
      format: 'FASTQ',
    },
    {
      accession: 'GHGAF99999999999014',
      ega_accession: 'EGAF99999914',
      alias: 'aligned_reads_003.bam',
      name: 'Aligned Reads 003',
      format: 'BAM',
    },
    {
      accession: 'GHGAF99999999999015',
      ega_accession: 'EGAF99999915',
      alias: 'chip_peaks_002.bed',
      name: 'ChIP Peaks 002',
      format: 'BED',
    },
    // No match in upload box (metadata-only):
    {
      accession: 'GHGAF99999999999016',
      ega_accession: 'EGAF99999916',
      alias: 'some_unessential_data.csv',
      name: 'Some Unessential Data',
      format: 'CSV',
    },
  ],
};
