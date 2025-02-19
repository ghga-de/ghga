/**
 * Short module description
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

export interface DatasetInformation {
  accession: string;
  file_information: FileInformation[];
}

export interface FileInformation {
  accession: string;
  // the remaining fields may be undefined
  // if the file exists, but information is not yet registered
  size?: number;
  sha256_hash?: string;
  storage_alias?: string;
}

export const emptyDatasetInformation: DatasetInformation = {
  accession: '',
  file_information: [],
};
