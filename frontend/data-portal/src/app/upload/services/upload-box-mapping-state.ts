/**
 * In-memory state service for the upload box file mapping tool.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Injectable, signal } from '@angular/core';
import { MappedField } from '../models/mapping';

/** Persisted state for a single upload box mapping session */
export interface MappingSnapshot {
  /** The selected study accession */
  studyAccession: string | undefined;
  /** The committed mapped field */
  mappedField: MappedField | undefined;
  /** Manual mappings serialised as Map entries (JSON-serialisable) */
  manualMappings: [string, string | null][];
}

/**
 * Root-level in-memory store for upload box mapping state.
 * Keyed by box ID so multiple boxes can have independent snapshots.
 * Instantiated lazily — only created when a data steward opens the mapping tool.
 */
@Injectable({ providedIn: 'root' })
export class UploadBoxMappingStateService {
  readonly #snapshots = signal<Map<string, MappingSnapshot>>(new Map());

  /**
   * Retrieve the saved snapshot for a box, or undefined if none exists.
   * @param boxId - the upload box ID
   * @returns the stored snapshot, or undefined
   */
  snapshotFor(boxId: string): MappingSnapshot | undefined {
    return this.#snapshots().get(boxId);
  }

  /**
   * Persist the current mapping state for a box.
   * @param boxId - the upload box ID
   * @param snapshot - the state to store
   */
  saveSnapshot(boxId: string, snapshot: MappingSnapshot): void {
    this.#snapshots.update((map) => new Map(map).set(boxId, snapshot));
  }

  /**
   * Remove the stored snapshot for a box (e.g. after submit or explicit cancel).
   * @param boxId - the upload box ID
   */
  clearSnapshot(boxId: string): void {
    this.#snapshots.update((map) => {
      const next = new Map(map);
      next.delete(boxId);
      return next;
    });
  }
}
