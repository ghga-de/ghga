/**
 * Dataset model
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

export interface DatasetFile {
  id: string;
  extension: string;
}

export interface Dataset {
  id: string;
  title: string;
  description: string;
  stage: 'download' | 'upload';
  files: DatasetFile[];
}

export interface DatasetWithExpiration extends Dataset {
  expires: string;
}
