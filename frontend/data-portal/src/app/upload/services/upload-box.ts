/**
 * Service handling research upload boxes.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpClient, HttpParams, httpResource } from '@angular/common/http';
import { computed, inject, Injectable, signal } from '@angular/core';
import { ConfigService } from '@app/shared/services/config';
import { map, Observable } from 'rxjs';
import {
  BoxRetrievalResults,
  ResearchDataUploadBox,
  ResearchDataUploadBoxBase,
  ResearchDataUploadBoxUpdate,
  UploadBoxFilter,
} from '../models/box';
import { FileUploadWithAccession } from '../models/file-upload';
import {
  GrantId,
  GrantWithBoxInfo,
  UploadGrant,
  UploadGrantBase,
} from '../models/grant';

/**
 * Service for managing upload boxes.
 */
@Injectable({ providedIn: 'root' })
export class UploadBoxService {
  #config = inject(ConfigService);
  #http = inject(HttpClient);
  #uosUrl = this.#config.uosUrl;
  #boxesUrl = `${this.#uosUrl}/boxes`;
  #accessGrantsUrl = `${this.#uosUrl}/access-grants`;
  #wkvsUrl = this.#config.wkvsUrl;
  #storageLabelsUrl = `${this.#wkvsUrl}/values/storage_labels`;

  #loadAllUploadBoxes = signal<boolean>(false);
  #loadStorageLabels = signal<boolean>(false);
  #uploadBoxesFilter = signal<UploadBoxFilter | undefined>(undefined);
  #loadSingleBox = signal<string>('');
  #loadGrantsForBox = signal<string>('');
  #loadFileUploadsForBox = signal<string>('');

  #emptyBoxResults: BoxRetrievalResults = {
    count: 0,
    boxes: [],
  };

  /**
   * Resource for loading all upload boxes.
   */
  boxRetrievalResults = httpResource<BoxRetrievalResults>(
    () => (this.#loadAllUploadBoxes() ? this.#boxesUrl : undefined),
    {
      defaultValue: this.#emptyBoxResults,
    },
  );

  /**
   * Resource for loading human-readable storage labels.
   */
  storageLabels = httpResource<Record<string, string>>(
    () =>
      this.#loadAllUploadBoxes() || this.#loadStorageLabels()
        ? this.#storageLabelsUrl
        : undefined,
    {
      parse: (raw) =>
        (raw as { storage_labels?: Record<string, string> }).storage_labels ?? {},
      defaultValue: {},
    },
  );

  /**
   * Resource for loading upload grants for a specific box.
   */
  boxGrants = httpResource<UploadGrant[]>(
    () => {
      const boxId = this.#loadGrantsForBox();
      if (!boxId) return undefined;
      return `${this.#accessGrantsUrl}?box_id=${encodeURIComponent(boxId)}`;
    },
    { defaultValue: [] },
  );

  /**
   * Resource for loading file uploads for a specific box.
   */
  boxFileUploads = httpResource<FileUploadWithAccession[]>(
    () => {
      const boxId = this.#loadFileUploadsForBox();
      if (!boxId) return undefined;
      return `${this.#boxesUrl}/${encodeURIComponent(boxId)}/uploads`;
    },
    { defaultValue: [] },
  );

  /**
   * Resource for loading a single upload box.
   */
  uploadBox = httpResource<ResearchDataUploadBox>(
    () => {
      const id = this.#loadSingleBox();
      if (!id) return undefined;
      return `${this.#uosUrl}/box/${id}`;
    },
    {
      defaultValue: undefined,
      parse: (raw) => raw as ResearchDataUploadBox,
    },
  );

  /**
   * Signal for all currently loaded upload boxes.
   */
  uploadBoxes = computed(() => {
    if (this.boxRetrievalResults.error()) return [];
    return this.boxRetrievalResults.value().boxes;
  });

  /**
   * The currently active filter applied to `filteredUploadBoxes`.
   */
  uploadBoxesFilter = computed(
    () =>
      this.#uploadBoxesFilter() ?? {
        title: undefined,
        state: undefined,
        location: undefined,
      },
  );

  /**
   * Signal for upload boxes filtered by the active filter state.
   */
  filteredUploadBoxes = computed(() => {
    let boxes = this.uploadBoxes();
    const filter = this.#uploadBoxesFilter();
    if (!boxes.length || !filter) return boxes;

    const title = filter.title?.trim().toLowerCase();
    if (title) {
      boxes = boxes.filter((box) => box.title.toLowerCase().includes(title));
    }

    if (filter.state) {
      const stateFilter = filter.state;
      if (stateFilter.startsWith('not_')) {
        const excluded = stateFilter.slice(4);
        boxes = boxes.filter((box) => box.state !== excluded);
      } else {
        boxes = boxes.filter((box) => box.state === stateFilter);
      }
    }

    const location = filter.location?.trim().toLowerCase();
    if (location) {
      boxes = boxes.filter(
        (box) => box.storage_alias.trim().toLowerCase() === location,
      );
    }

    return boxes;
  });

  /**
   * All locations available in the loaded upload boxes.
   */
  uploadBoxLocations = computed(() => {
    const uniqueLocations = new Set<string>(
      this.uploadBoxes().map((box: ResearchDataUploadBox) => box.storage_alias),
    );
    return Array.from(uniqueLocations).sort((left, right) => left.localeCompare(right));
  });

  /**
   * All available upload-box locations including display labels.
   */
  uploadBoxLocationOptions = computed(() => {
    const labels = this.storageLabels.error() ? {} : this.storageLabels.value();
    return this.uploadBoxLocations()
      .map((locationAlias) => ({
        value: locationAlias,
        label: labels[locationAlias] ?? locationAlias,
      }))
      .sort((left, right) => left.label.localeCompare(right.label));
  });

  /**
   * Trigger loading of storage location labels from the WKVS backend.
   */
  loadStorageLabels(): void {
    this.#loadStorageLabels.set(true);
  }

  /**
   * Trigger loading of all upload boxes from the UOS backend.
   */
  loadAllUploadBoxes(): void {
    this.#loadAllUploadBoxes.set(true);
  }

  /**
   * Trigger loading of a single upload box by ID.
   * @param id - the ID of the upload box to load
   */
  loadUploadBox(id: string): void {
    this.#loadSingleBox.set(id);
  }

  /**
   * Trigger loading of upload grants for a specific box.
   * @param boxId - the ID of the upload box
   */
  loadBoxGrants(boxId: string): void {
    this.#loadGrantsForBox.set(boxId);
  }

  /**
   * Trigger loading of file uploads for a specific box.
   * @param boxId - the ID of the upload box
   */
  loadFileUploadsForBox(boxId: string): void {
    this.#loadFileUploadsForBox.set(boxId);
  }

  /**
   * Create a new upload box.
   * @param data - the base data for the new upload box
   * @returns An observable that emits the ID of the created box
   */
  createUploadBox(data: ResearchDataUploadBoxBase): Observable<string> {
    return this.#http
      .post<{ id: string }>(this.#boxesUrl, data)
      .pipe(map((response) => response.id));
  }

  /**
   * Update an existing upload box.
   * @param id - the ID of the upload box to update
   * @param changes - the fields to update
   * @returns An observable that completes when the update is successful
   */
  updateUploadBox(id: string, changes: ResearchDataUploadBoxUpdate): Observable<void> {
    return this.#http.patch<void>(`${this.#boxesUrl}/${id}`, changes);
  }

  /**
   * Set the active filter for the upload box list.
   * @param filter - the filter to apply
   */
  setUploadBoxesFilter(filter: UploadBoxFilter): void {
    this.#uploadBoxesFilter.set(filter);
  }

  /**
   * Resolve a storage alias to a human-readable storage location label.
   * @param storageAlias - the alias from a box item
   * @returns the human-readable label, or the alias itself if unknown
   */
  getStorageLocationLabel(storageAlias: string): string {
    if (this.storageLabels.error()) return storageAlias;
    return this.storageLabels.value()[storageAlias] ?? storageAlias;
  }

  /**
   * Fetch access grants from the UOS backend.
   * @param params - optional filter parameters
   * @param params.userId - filter by user ID (maps to the `userid` query param)
   * @param params.boxId - filter by box ID (maps to the `box_id` query param)
   * @param params.valid - true = valid only, false = invalid only, null/omitted = both
   * @returns An observable that emits an array of GrantWithBoxInfo objects
   */
  getAccessGrants(params?: {
    userId?: string;
    boxId?: string;
    valid?: boolean | null;
  }): Observable<GrantWithBoxInfo[]> {
    let httpParams = new HttpParams();
    if (params?.userId) httpParams = httpParams.set('userid', params.userId);
    if (params?.boxId) httpParams = httpParams.set('box_id', params.boxId);
    if (params?.valid != null)
      httpParams = httpParams.set('valid', String(params.valid));
    return this.#http.get<GrantWithBoxInfo[]>(this.#accessGrantsUrl, {
      params: httpParams,
    });
  }

  /**
   * Add a new upload grant locally to avoid re-fetching from backend.
   * @param grant - the fully constructed grant to add
   */
  addGrantLocally(grant: UploadGrant): void {
    if (!this.boxGrants.error()) {
      this.boxGrants.value.set([...this.boxGrants.value(), grant]);
    }
  }

  /**
   * Create a new upload grant.
   * @param data - the base data for the new upload grant
   * @returns An observable that emits the server-assigned id and created timestamp
   */
  createUploadGrant(data: UploadGrantBase): Observable<GrantId> {
    return this.#http.post<GrantId>(this.#accessGrantsUrl, data);
  }

  /**
   * Revoke an upload grant by its ID.
   * @param id - the ID of the upload grant to revoke
   * @returns An observable that completes when the grant is revoked
   */
  revokeUploadGrant(id: string): Observable<void> {
    return this.#http.delete<void>(`${this.#accessGrantsUrl}/${id}`);
  }
}
