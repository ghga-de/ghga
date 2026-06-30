/**
 * Interface for the storage aliases.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

export interface wellKnownValues {
  [key: string]: string;
}

export interface BaseStorageLabels {
  storage_labels: wellKnownValues;
}

export const emptyStorageLabels: wellKnownValues = {};
