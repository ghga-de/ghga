/**
 * Mock data to be used in MSW responses
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DatasetDetails } from '@app/metadata/models/dataset-details';
import { DatasetInformation } from '@app/metadata/models/dataset-information';
import { DatasetSummary } from '@app/metadata/models/dataset-summary';
import { BaseGlobalSummary } from '@app/metadata/models/global-summary';
import { SearchResults } from '@app/metadata/models/search-results';
import { IvaState, IvaType, UserWithIva } from '@app/verification-addresses/models/iva';
import { Dataset } from '@app/work-packages/models/dataset';
import { WorkPackageResponse } from '@app/work-packages/models/work-package';

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
];

export const allIvasOfDoe = allIvas.filter((iva) => iva.user_id === 'doe@test.dev');
export const allIvasOfRoe = allIvas.filter((iva) => iva.user_id === 'roe@test.dev');

/**
 * Metldata API
 */

// get dataset summaries with arbitrary accessions
export const getDatasetSummary = (accession: string) => ({
  ...datasetSummary,
  accession: accession,
});

// get embedded datasets with arbitrary accessions
export const getDatasetDetails = (accession: string) => ({
  ...datasetDetails,
  accession: accession,
  ega_accession: accession.replace('GHGA', 'EGA'),
});

export const metadataGlobalSummary: BaseGlobalSummary = {
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
    },
  },
};

export const datasetSummary: DatasetSummary = {
  accession: 'GHGAD12345678901234',
  description:
    'This is the test dataset description. Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.\nVel risus commodo viverra maecenas accumsan lacus vel. Sit amet risus nullam eget felis eget nunc lobortis mattis. Iaculis at erat pellentesque adipiscing commodo. Volutpat consequat mauris nunc congue. At lectus urna duis convallis convallis tellus id interdum velit. Gravida cum sociis natoque penatibus et. Mauris in aliquam sem fringilla ut morbi. Ultrices gravida dictum fusce ut. At consectetur lorem donec massa sapien faucibus et molestie.',
  types: ['Test Type'],
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
        { value: 'Test Phenotype 1', count: 2 },
        { value: 'Test Phenotype 2', count: 1 },
        { value: 'Test Phenotype 3', count: 1 },
      ],
    },
  },
  studies_summary: {
    count: 1,
    stats: {
      accession: 'GHGAS12345678901234',
      title: 'Test Study',
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

export const datasetDetails: DatasetDetails = {
  accession: 'GHGAD12345678901234',
  title: 'Test dataset for details',
  description:
    'Test dataset with some details for testing. Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Vel risus commodo viverra maecenas accumsan lacus vel. Sit amet risus nullam eget felis eget nunc lobortis mattis. Iaculis at erat pellentesque adipiscing commodo. Volutpat consequat mauris nunc congue. At lectus urna duis convallis convallis tellus id interdum velit. Gravida cum sociis natoque penatibus et. Mauris in aliquam sem fringilla ut morbi. Ultrices gravida dictum fusce ut. At consectetur lorem donec massa sapien faucibus et molestie.',
  types: ['Test Type'],
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
  },
  study: {
    accession: 'GHGAS12345678901234',
    ega_accession: 'EGAS12345678901',
    types: ['test_genomics'],
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
      experiment_method: {
        accession: 'GHGAEM12345678901234',
        name: 'DNA-Seq',
        type: 'Experiment Method 1',
        instrument_model: 'Experiment Platform 1',
      },
    },
    {
      accession: 'GHGAE12345678901235',
      ega_accession: 'EGAE12345678902',
      title: 'Text Experiment 2',
      description: 'Test Experiment 2. Sagittis purus sit amet volutpat.',
      experiment_method: {
        accession: 'GHGAEM12345678901235',
        name: 'RNA-Seq',
        type: 'Experiment Method 2',
        instrument_model: 'Experiment Platform 2',
      },
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
      individual: {
        sex: 'Female',
        phenotypic_features_terms: ['Test phenotypic feature 1'],
      },
      biospecimen_type: 'Test biospeciment type 1',
      biospecimen_tissue_term: 'Test tissue',
    },
    {
      accession: 'GHGAN12345678901235',
      ega_accession: 'EGAN12345678904',
      description: 'Test Sample 2. Vivamus arcu felis bibendum ut.',
      name: 'Test anatomical entity 2',
      case_control_status: 'Test control status 2',
      individual: {
        sex: 'Male',
        phenotypic_features_terms: ['Test phenotypic feature 2'],
      },
      biospecimen_type: 'Test biospeciment type 2',
      biospecimen_tissue_term: 'Test tissue 2',
    },
    {
      accession: 'GHGAN12345678901236',
      ega_accession: 'EGAN12345678905',
      description: 'Test Sample 3. Vivamus arcu felis bibendum ut.',
      name: 'Test anatomical entity 3',
      case_control_status: 'Test control status 3',
      individual: {
        sex: 'Female',
        phenotypic_features_terms: ['Test phenotypic feature 3'],
      },
      biospecimen_type: 'Test biospeciment type 3',
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
  count: 26, // just to test the paginator
  hits: [
    {
      id_: 'GHGAD12345678901234',
      content: {
        alias: 'EGAD12345678901',
        title:
          'Test dataset for details and this is also testing whether two lines of text actually appear correctly on the expansion panel headers or not at least at a resolution of one thousand nine hundred and twenty pixels wide',
      },
    },
    {
      id_: 'GHGAD12345678901235',
      content: {
        alias: 'EGAD12345678902',
        title: 'Test dataset for details',
      },
    },
    {
      id_: 'GHGAD12345678901236',
      content: {
        alias: 'EGAD12345678903',
        title:
          'Test dataset for details and this is also testing whether more than two lines of text actually appear correctly on the expansion panel headers or not at least at a resolution of one thousand nine hundred and twenty pixels wide especially since this can cause issues with the layout of the expansion panels',
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
  },
  {
    id: '4ef4ccac-6c0a-4be6-9637-b33925178cea',
    user_id: 'doe@test.dev',
    dataset_id: 'GHGAD12345678901235',
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
  },
  {
    id: '4ef4ccac-6c0a-4be6-9637-b339251793fb',
    user_id: 'doe@test.dev',
    dataset_id: 'GHGAD12345678901235',
    full_user_name: 'Dr. John Doe',
    email: 'j.jdoe@home.org',
    request_text:
      'This is a test request for dataset GHGAD12345678901235. It is expired.',
    access_starts: dateOneYearAgo,
    access_ends: dateYesterday,
    request_created: '2023-05-11T12:04:02.000Z',
    status: 'allowed',
    status_changed: '2023-05-19T12:04:03.000Z',
    changed_by: 'doe@test.dev',
    iva_id: '783d9682-d5e5-4ce7-9157-9eeb53a1e9ba',
  },
  {
    id: 'a787d591-4264-4f48-8827-598585db868e',
    user_id: 'doe@test.dev',
    dataset_id: 'GHGAD12345678901236',
    full_user_name: 'Dr. John Doe',
    email: 'doe@home.org',
    request_text: 'This is a test request for dataset GHGAD12345678901236.',
    access_starts: access_starts,
    access_ends: access_ends,
    request_created: '2023-05-18T12:04:03.000Z',
    status: 'denied',
    status_changed: '2023-05-19T12:04:02.000Z',
    changed_by: 'doe@test.dev',
  },
  {
    id: '9409db13-e23e-433e-9afa-544d8f25b720',
    user_id: 'doe@test.dev',
    dataset_id: 'GHGAD12345678901236',
    full_user_name: 'Dr. John Doe',
    email: 'doe@home.org',
    request_text: 'This is a test request for dataset GHGAD12345678901236.',
    access_starts: access_starts,
    access_ends: access_ends,
    request_created: '2023-05-18T12:04:03.000Z',
    status: 'pending',
    status_changed: '2023-05-19T12:04:02.000Z',
    changed_by: 'doe@test.dev',
  },
];

export const getAccessRequests = (user_id?: string, dataset_id?: string) =>
  accessRequests.filter(
    (x) =>
      (!dataset_id || x.dataset_id === dataset_id) &&
      (!user_id || x.user_id === user_id),
  );

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
 * WPS API
 */

export const datasets: Dataset[] = [
  {
    id: 'GHGAD12345678901234',
    title: 'Some dataset to upload',
    description:
      'This is a very interesting dataset that can be used' +
      ' to test the upload functionality of the Data Portal.' +
      ' Note that the description can be longer than the title.',
    stage: 'upload',
    files: [],
  },
  {
    id: 'GHGAD12345678901235',
    title: 'Some dataset to download',
    description:
      'This is a very interesting dataset that can be used' +
      ' to test the download functionality of the Data Portal.' +
      ' Note that the description can be longer than the title.',
    stage: 'download',
    files: [],
  },
  {
    id: 'GHGAD12345678901236',
    title: 'Another dataset to download',
    description:
      'This is another todally ineresting dataset that can be used' +
      ' to test the download functionality of the Data Portal.' +
      ' Note that the description can be longer than the title.',
    stage: 'download',
    files: [],
  },
];

export const workPackageResponse: WorkPackageResponse = {
  id: '7f562eb5-a0a5-427d-b40f-f91198d27309',
  // the encrypted work package token (which can be pretty long)
  token:
    'gumRa5XE1Rm3tOJr3ocfA1F63rRUI2g6eCI0KY2Mv3epb28cZeylvaYsxRmgQRDboE2yOhtE4qxPhZgYz/Y7zR+hssBzq7Hg',
};
