/**
 * Service handling research upload boxes.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpClient, HttpParams, httpResource } from '@angular/common/http';
import { computed, inject, resource, Service, signal } from '@angular/core';
import { AuthService } from '@app/auth/services/auth';
import { ConfigService } from '@app/shared/services/config';
import { volatileCacheContext } from '@app/shared/utils/http-cache';
import { CacheBucket, HttpCacheManager } from '@ngneat/cashew';
import { firstValueFrom, fromEvent, map, Observable, takeUntil, tap } from 'rxjs';
import { AccessionMapRequest } from '../models/accession-map';
import {
  BoxRetrievalResults,
  ResearchDataUploadBox,
  ResearchDataUploadBoxBase,
  ResearchDataUploadBoxUpdate,
  UploadBoxFilter,
  UploadBoxState,
} from '../models/box';
import {
  BoxUploadsPage,
  DEFAULT_UPLOADS_PAGE_SIZE,
  emptyBoxUploadsPage,
  FileUploadSortDirection,
  fileUploadSortSpec,
  fileUploadSortState,
  FileUploadWithAccession,
  MAX_UPLOADS_PAGE_SIZE,
} from '../models/file-upload';
import {
  GrantId,
  GrantWithBoxInfo,
  UploadGrant,
  UploadGrantBase,
} from '../models/grant';

/**
 * Service for managing upload boxes.
 */
@Service()
export class UploadBoxService {
  #auth = inject(AuthService);
  #config = inject(ConfigService);
  #http = inject(HttpClient);
  #httpCache = inject(HttpCacheManager);
  #userId = computed<string | undefined>(() => this.#auth.user()?.id || undefined);
  #rsUrl = this.#config.rsUrl;
  #boxesUrl = `${this.#rsUrl}/upload-boxes`;
  #grantsUrl = `${this.#rsUrl}/upload-grants`;
  #wkvsUrl = this.#config.wkvsUrl;
  #storageLabelsUrl = `${this.#wkvsUrl}/values/storage_labels`;

  // All GET requests are cached by the cashew interceptor (see app.config.ts),
  // keyed by their URL including query parameters. Reloading a resource without
  // dropping its cache entry first would simply replay the cached body, so every
  // resource below collects its cache keys in a bucket. Deleting a bucket
  // invalidates all variants of that endpoint at once, which matters for the
  // paginated and sorted file uploads, where the keys are not known upfront.
  #boxesBucket = new CacheBucket();
  #boxBucket = new CacheBucket();
  #boxGrantsBucket = new CacheBucket();
  #userGrantsBucket = new CacheBucket();
  #fileUploadsBucket = new CacheBucket();

  #boxesContext = volatileCacheContext(this.#boxesBucket);
  #boxContext = volatileCacheContext(this.#boxBucket);
  #boxGrantsContext = volatileCacheContext(this.#boxGrantsBucket);
  #userGrantsContext = volatileCacheContext(this.#userGrantsBucket);
  #fileUploadsContext = volatileCacheContext(this.#fileUploadsBucket);

  #loadAllUploadBoxes = signal<boolean>(false);
  #loadStorageLabels = signal<boolean>(false);
  #uploadBoxesFilter = signal<UploadBoxFilter | undefined>(undefined);
  #loadSingleBox = signal<string>('');
  #loadGrantsForBox = signal<string>('');

  // Query state for the paginated file uploads of a single box. The RS serves
  // this endpoint page by page, so skip, limit and sort are sent to the server
  // instead of being applied to a fully loaded list in the browser.
  #loadFileUploadsForBox = signal<string>('');
  #fileUploadsSkip = signal<number>(0);
  #fileUploadsLimit = signal<number>(DEFAULT_UPLOADS_PAGE_SIZE);
  #fileUploadsSort = signal<string | undefined>(undefined);

  #loadAllFileUploadsForBox = signal<string>('');

  #emptyBoxResults: BoxRetrievalResults = {
    count: 0,
    boxes: [],
  };

  /**
   * Resource for loading all upload boxes.
   */
  boxRetrievalResults = httpResource<BoxRetrievalResults>(
    () =>
      this.#loadAllUploadBoxes()
        ? { url: this.#boxesUrl, context: this.#boxesContext }
        : undefined,
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
      return {
        url: `${this.#grantsUrl}?box_id=${encodeURIComponent(boxId)}`,
        context: this.#boxGrantsContext,
      };
    },
    { defaultValue: [] },
  );

  /**
   * Resource for loading the current user's valid upload grants with box info.
   */
  userGrants = httpResource<GrantWithBoxInfo[]>(
    () => {
      const userId = this.#userId();
      if (!userId) return undefined;
      return {
        url: `${this.#grantsUrl}?user_id=${encodeURIComponent(userId)}&valid=true`,
        context: this.#userGrantsContext,
      };
    },
    { defaultValue: [] },
  );

  /**
   * Build the request for a page of file uploads of a box.
   * @param boxId - the ID of the upload box
   * @param skip - the number of file uploads to skip
   * @param limit - the maximum number of file uploads to return
   * @param sort - the comma-separated sort specification, if any
   * @returns the HTTP resource request for the requested page
   */
  #fileUploadsRequest(boxId: string, skip: number, limit: number, sort?: string) {
    const params: Record<string, string | number> = { skip, limit };
    if (sort) params['sort'] = sort;
    return {
      url: `${this.#boxesUrl}/${encodeURIComponent(boxId)}/uploads`,
      params,
      context: this.#fileUploadsContext,
    };
  }

  /**
   * Resource for loading one page of file uploads for a specific box.
   *
   * Pagination and sorting happen on the server: the current page and sort order
   * are part of the request, so changing them refetches instead of reslicing a
   * locally cached list.
   */
  boxFileUploads = httpResource<BoxUploadsPage>(
    () => {
      const boxId = this.#loadFileUploadsForBox();
      if (!boxId) return undefined;
      return this.#fileUploadsRequest(
        boxId,
        this.#fileUploadsSkip(),
        this.#fileUploadsLimit(),
        this.#fileUploadsSort(),
      );
    },
    { defaultValue: emptyBoxUploadsPage },
  );

  /**
   * Resource for loading the complete list of file uploads for a specific box.
   *
   * Used by consumers that must reason about all files at once (file mapping and
   * metadata alignment) rather than showing them page by page. Since the RS caps
   * the page size, this walks through as many pages as the box needs, so boxes of
   * any size are covered in full. It is therefore a plain `resource` rather than
   * an `httpResource`, which could only issue a single request.
   */
  allBoxFileUploads = resource<FileUploadWithAccession[], string | undefined>({
    params: () => this.#loadAllFileUploadsForBox() || undefined,
    loader: async ({ params: boxId, abortSignal }) => {
      const files: FileUploadWithAccession[] = [];
      let totalCount = 0;
      do {
        const { url, params, context } = this.#fileUploadsRequest(
          boxId,
          files.length,
          MAX_UPLOADS_PAGE_SIZE,
        );
        // Unsubscribing on abort cancels the in-flight request, so navigating
        // away mid-walk does not keep fetching pages nobody waits for.
        const page = await firstValueFrom(
          this.#http
            .get<BoxUploadsPage>(url, { params, context })
            .pipe(takeUntil(fromEvent(abortSignal, 'abort'))),
        );
        totalCount = page.total_count;
        files.push(...page.items);
        // Guard against a page that reports more files than it ever delivers,
        // which would otherwise keep requesting the same offset forever.
        if (!page.items.length) break;
      } while (files.length < totalCount);
      return files;
    },
    defaultValue: [],
  });

  /** The file uploads on the currently loaded page. */
  boxFiles = computed<FileUploadWithAccession[]>(() =>
    this.boxFileUploads.error() ? [] : this.boxFileUploads.value().items,
  );

  /** The total number of file uploads in the box the current page belongs to. */
  boxFilesTotalCount = computed<number>(() =>
    this.boxFileUploads.error() ? 0 : this.boxFileUploads.value().total_count,
  );

  /** The number of file uploads currently skipped for pagination. */
  boxFilesSkip = computed<number>(() => this.#fileUploadsSkip());

  /** The current page size for the paginated file uploads. */
  boxFilesLimit = computed<number>(() => this.#fileUploadsLimit());

  /** The current sort specification for the paginated file uploads, if any. */
  boxFilesSort = computed<string | undefined>(() => this.#fileUploadsSort());

  /** The sorted column and direction of the paginated file uploads. */
  boxFilesSortState = computed(() => fileUploadSortState(this.#fileUploadsSort()));

  /** The complete list of file uploads of the box loaded via `loadAllFileUploadsForBox`. */
  allBoxFiles = computed<FileUploadWithAccession[]>(() =>
    this.allBoxFileUploads.error() ? [] : this.allBoxFileUploads.value(),
  );

  /**
   * Resource for loading a single upload box.
   */
  uploadBox = httpResource<ResearchDataUploadBox>(
    () => {
      const id = this.#loadSingleBox();
      if (!id) return undefined;
      return { url: `${this.#boxesUrl}/${id}`, context: this.#boxContext };
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
   * All available upload-box locations including display labels.
   */
  uploadBoxLocationOptions = computed(() => {
    const labels = this.storageLabels.error() ? {} : this.storageLabels.value();
    return Object.keys(labels)
      .map((locationAlias) => ({
        value: locationAlias,
        label: labels[locationAlias],
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
   * Trigger loading of all upload boxes from the RS backend.
   */
  loadAllUploadBoxes(): void {
    this.#loadAllUploadBoxes.set(true);
  }

  /**
   * Fetch all upload boxes again, bypassing the HTTP cache.
   * Boxes change outside the portal (files are uploaded with the GHGA Connector),
   * so entering the box list must not rely on what was fetched earlier.
   */
  reloadAllUploadBoxes(): void {
    this.#httpCache.delete(this.#boxesBucket);
    if (this.#loadAllUploadBoxes()) {
      this.boxRetrievalResults.reload();
    } else {
      this.loadAllUploadBoxes();
    }
  }

  /**
   * Trigger loading of a single upload box by ID.
   * @param id - the ID of the upload box to load
   */
  loadUploadBox(id: string): void {
    this.#loadSingleBox.set(id);
  }

  /**
   * Fetch a single upload box again, bypassing the HTTP cache.
   * Requesting the box that is already loaded would otherwise not issue any
   * request at all, since the resource request would remain unchanged.
   * @param id - the ID of the upload box to load
   */
  reloadUploadBox(id: string): void {
    this.#httpCache.delete(this.#boxBucket);
    if (this.#loadSingleBox() === id) {
      this.uploadBox.reload();
    } else {
      this.loadUploadBox(id);
    }
  }

  /**
   * Trigger loading of upload grants for a specific box.
   * @param boxId - the ID of the upload box
   */
  loadBoxGrants(boxId: string): void {
    this.#loadGrantsForBox.set(boxId);
  }

  /**
   * Fetch the upload grants of a specific box again, bypassing the HTTP cache.
   * @param boxId - the ID of the upload box
   */
  reloadBoxGrants(boxId: string): void {
    this.#httpCache.delete(this.#boxGrantsBucket);
    if (this.#loadGrantsForBox() === boxId) {
      this.boxGrants.reload();
    } else {
      this.loadBoxGrants(boxId);
    }
  }

  /**
   * Fetch the current user's upload grants again, bypassing the HTTP cache.
   * This resource has no explicit load trigger: it starts as soon as the user
   * is known and would otherwise never be fetched again during the session,
   * so grants created in the meantime would stay invisible on the account page.
   */
  reloadUserGrants(): void {
    this.#httpCache.delete(this.#userGrantsBucket);
    this.userGrants.reload();
  }

  /**
   * Trigger loading of the first page of file uploads for a specific box.
   * Switching to a different box resets pagination and sorting, so the caller
   * never inherits the page position of a previously inspected box.
   * @param boxId - the ID of the upload box
   */
  loadFileUploadsForBox(boxId: string): void {
    if (this.#loadFileUploadsForBox() !== boxId) {
      this.#fileUploadsSkip.set(0);
      this.#fileUploadsLimit.set(DEFAULT_UPLOADS_PAGE_SIZE);
      this.#fileUploadsSort.set(undefined);
    }
    this.#loadFileUploadsForBox.set(boxId);
  }

  /**
   * Fetch the file uploads of a box again, bypassing the HTTP cache.
   * Files are uploaded with the GHGA Connector rather than through the portal,
   * so the file list changes without any action taken here and can only be kept
   * up to date by fetching it again.
   * @param boxId - the ID of the upload box
   */
  reloadFileUploadsForBox(boxId: string): void {
    this.#httpCache.delete(this.#fileUploadsBucket);
    if (this.#loadFileUploadsForBox() === boxId) {
      this.boxFileUploads.reload();
    } else {
      this.loadFileUploadsForBox(boxId);
    }
    if (this.#loadAllFileUploadsForBox() === boxId) {
      this.allBoxFileUploads.reload();
    }
  }

  /**
   * Request a different page of the file uploads of the currently loaded box.
   * @param limit - the page size
   * @param skip - the number of file uploads to skip
   */
  paginateFileUploads(limit: number, skip: number): void {
    this.#fileUploadsLimit.set(Math.min(limit, MAX_UPLOADS_PAGE_SIZE));
    this.#fileUploadsSkip.set(skip);
  }

  /**
   * Change the sort order of the file uploads of the currently loaded box and
   * jump back to the first page, since the previous offset is meaningless in the
   * new order.
   * @param sort - comma-separated `FileUpload` field names, each optionally
   *   prefixed with "-" for descending order, or undefined for the default order
   */
  sortFileUploads(sort: string | undefined): void {
    this.#fileUploadsSort.set(sort || undefined);
    this.#fileUploadsSkip.set(0);
  }

  /**
   * Sort the file uploads of the currently loaded box by a table column.
   * @param column - the sorted column of the file uploads table
   * @param direction - the direction the column is sorted in
   */
  sortFileUploadsByColumn(column: string, direction: FileUploadSortDirection): void {
    this.sortFileUploads(fileUploadSortSpec(column, direction));
  }

  /**
   * Trigger loading of the complete file upload list for a specific box.
   * @param boxId - the ID of the upload box
   */
  loadAllFileUploadsForBox(boxId: string): void {
    this.#loadAllFileUploadsForBox.set(boxId);
  }

  /**
   * Create a new upload box.
   * @param data - the base data for the new upload box
   * @returns An observable that emits the ID of the created box
   */
  createUploadBox(data: ResearchDataUploadBoxBase): Observable<string> {
    return this.#http.post<string>(this.#boxesUrl, data).pipe(
      map((id) => {
        this.#addUploadBoxLocally(data, id);
        return id;
      }),
    );
  }

  /**
   * Add a newly created upload box locally to keep the list in sync without waiting for a reload.
   * @param data - creation payload
   * @param id - server-generated upload box ID
   */
  #addUploadBoxLocally(data: ResearchDataUploadBoxBase, id: string): void {
    this.#invalidateBoxes();
    if (
      this.boxRetrievalResults.error() ||
      typeof this.boxRetrievalResults.value.set !== 'function'
    ) {
      return;
    }

    const newBox: ResearchDataUploadBox = {
      id,
      version: 1,
      state: UploadBoxState.open,
      title: data.title,
      description: data.description,
      storage_alias: data.storage_alias,
      max_size: data.max_size,
      last_changed: new Date().toISOString(),
      changed_by: this.#auth.user()?.id ?? '',
      file_count: 0,
      size: 0,
    };

    const current = this.boxRetrievalResults.value();
    this.boxRetrievalResults.value.set({
      count: current.count + 1,
      boxes: [...current.boxes, newBox],
    });
  }

  /**
   * Update the box state locally to avoid waiting for reload.
   * @param id - the ID of the updated upload box
   * @param changes - the changes to the upload box which may be partial
   */
  #updateUploadBoxLocally(id: string, changes: Partial<ResearchDataUploadBox>): void {
    this.#invalidateBoxes();
    const expectedVersion = changes.version;
    if (expectedVersion === undefined) {
      return;
    }
    const version = expectedVersion + 1;
    if (!this.uploadBox.error()) {
      const oldBox = this.uploadBox.value();
      if (oldBox && oldBox.id === id && oldBox.version === expectedVersion) {
        const newBox = { ...oldBox, ...changes, version };
        this.uploadBox.value.set(newBox);
      }
    }
    if (!this.boxRetrievalResults.error()) {
      const oldBox = this.boxRetrievalResults.value().boxes.find((b) => b.id === id);
      if (oldBox && oldBox.version === expectedVersion) {
        const newBox = { ...oldBox, ...changes, version };
        const current = this.boxRetrievalResults.value();
        const update = (boxes: ResearchDataUploadBox[]) =>
          boxes.map((b) => (b.id === id ? newBox : b));
        this.boxRetrievalResults.value.set({
          count: current.count,
          boxes: update(current.boxes),
        });
      }
    }
    if (!this.userGrants.error()) {
      const oldGrant = this.userGrants.value().find((g) => g.box_id === id);
      if (oldGrant && oldGrant.box_version === expectedVersion) {
        const newGrant = { ...oldGrant };
        if ('state' in changes && changes.state !== undefined) {
          newGrant.box_state = changes.state;
        }
        if ('title' in changes && changes.title !== undefined) {
          newGrant.box_title = changes.title;
        }
        if ('description' in changes && changes.description !== undefined) {
          newGrant.box_description = changes.description;
        }
        newGrant.box_version = version;
        this.userGrants.value.set(
          this.userGrants.value().map((g) => (g.box_id === id ? newGrant : g)),
        );
      }
    }
  }

  /**
   * Update an existing upload box.
   * @param id - the ID of the upload box to update
   * @param changes - the fields to update
   * @returns An observable that completes when the update is successful
   */
  updateUploadBox(id: string, changes: ResearchDataUploadBoxUpdate): Observable<void> {
    return this.#http
      .patch<void>(`${this.#boxesUrl}/${id}`, changes)
      .pipe(tap(() => this.#updateUploadBoxLocally(id, changes)));
  }

  /**
   * Send a PATCH request to set the upload box state to locked (submitted).
   * @param boxId - the ID of the upload box
   * @param currentVersion - the current box version
   * @param force - lock even if some file uploads are still incomplete
   * @returns An observable that completes when the lock is accepted
   */
  lockUploadBox(
    boxId: string,
    currentVersion: number,
    force = false,
  ): Observable<void> {
    const changes: ResearchDataUploadBoxUpdate = {
      version: currentVersion,
      state: UploadBoxState.locked,
    };
    // `force` makes the backend lock the box despite incomplete uploads; it is
    // a request flag, not part of the persisted box state, so it is kept out of
    // the local update below. The backend only accepts it on the open→locked
    // transition, so it lives here rather than on the generic updateUploadBox.
    const body = force ? { ...changes, force: true } : changes;
    return this.#http
      .patch<void>(`${this.#boxesUrl}/${encodeURIComponent(boxId)}`, body)
      .pipe(tap(() => this.#updateUploadBoxLocally(boxId, changes)));
  }

  /**
   * Send a PATCH request to set the upload box state back to open.
   * Used by data stewards to reopen a locked upload box.
   * @param boxId - the ID of the upload box
   * @param currentVersion - the current box version
   * @returns An observable that completes when the reopening is accepted
   */
  openUploadBox(boxId: string, currentVersion: number): Observable<void> {
    const changes: ResearchDataUploadBoxUpdate = {
      version: currentVersion,
      state: UploadBoxState.open,
    };
    return this.#http
      .patch<void>(`${this.#boxesUrl}/${encodeURIComponent(boxId)}`, changes)
      .pipe(tap(() => this.#updateUploadBoxLocally(boxId, changes)));
  }

  /**
   * Delete an upload box and all of its files. The backend rejects deletion of
   * archived boxes, so callers should not offer this for archived boxes.
   * @param boxId - the ID of the upload box to delete
   * @param currentVersion - the current box version
   * @returns An observable that completes when the box is deleted
   */
  deleteUploadBox(boxId: string, currentVersion: number): Observable<void> {
    const url = `${this.#boxesUrl}/${encodeURIComponent(boxId)}`;
    const params = new HttpParams().set('version', String(currentVersion));
    return this.#http
      .delete<void>(url, { params })
      .pipe(tap(() => this.#removeUploadBoxLocally(boxId)));
  }

  /**
   * Remove a deleted upload box from local state so the list stays consistent
   * without a re-fetch.
   * @param boxId - the ID of the deleted upload box
   */
  #removeUploadBoxLocally(boxId: string): void {
    this.#invalidateBoxes();
    if (this.boxRetrievalResults.error()) return;
    const current = this.boxRetrievalResults.value();
    if (!current.boxes.some((b) => b.id === boxId)) return;
    this.boxRetrievalResults.value.set({
      count: Math.max(0, current.count - 1),
      boxes: current.boxes.filter((b) => b.id !== boxId),
    });
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
   * Fetch upload grants from the RS backend.
   * @param params - optional filter parameters
   * @param params.userId - filter by user ID (maps to the `user_id` query param)
   * @param params.boxId - filter by box ID (maps to the `box_id` query param)
   * @param params.valid - true = valid only, false = invalid only, null/omitted = both
   * @returns An observable that emits an array of GrantWithBoxInfo objects
   */
  getUploadGrants(params?: {
    userId?: string;
    boxId?: string;
    valid?: boolean | null;
  }): Observable<GrantWithBoxInfo[]> {
    let httpParams = new HttpParams();
    if (params?.userId) httpParams = httpParams.set('user_id', params.userId);
    if (params?.boxId) httpParams = httpParams.set('box_id', params.boxId);
    if (params?.valid != null)
      httpParams = httpParams.set('valid', String(params.valid));
    return this.#http.get<GrantWithBoxInfo[]>(this.#grantsUrl, {
      params: httpParams,
    });
  }

  /**
   * Add a new upload grant locally to avoid re-fetching from backend.
   * @param grant - the fully constructed grant to add
   */
  #addGrantLocally(grant: UploadGrant): void {
    if (!this.boxGrants.error()) {
      this.boxGrants.value.set([...this.boxGrants.value(), grant]);
    }
  }

  /**
   * Drop the cached grant responses after a grant has been created or revoked.
   * Only the per-box grant list is patched locally; the current user's grants
   * are served under a different URL and carry denormalised box information,
   * so they have to be fetched again rather than reconstructed here.
   */
  #invalidateGrants(): void {
    this.#httpCache.delete(this.#boxGrantsBucket);
    this.#httpCache.delete(this.#userGrantsBucket);
  }

  /**
   * Drop the cached box responses after a box has been created, changed or
   * deleted. The user's grants are dropped as well because they carry the box
   * title, description, state and version alongside the grant itself.
   */
  #invalidateBoxes(): void {
    this.#httpCache.delete(this.#boxesBucket);
    this.#httpCache.delete(this.#boxBucket);
    this.#httpCache.delete(this.#userGrantsBucket);
  }

  /**
   * Remove an upload grant locally to avoid re-fetching from backend.
   * @param id - the id of the grant to remove
   */
  #revokeGrantLocally(id: string): void {
    if (this.boxGrants.error() || typeof this.boxGrants.value.set !== 'function') {
      return;
    }

    this.boxGrants.value.set(this.boxGrants.value().filter((grant) => grant.id !== id));
  }

  /**
   * Create a new upload grant.
   * @param data - the base data for the new upload grant
   * @param user - optional user data for updating the local in-memory grant list
   * @param user.name - full name of the user without title
   * @param user.email - email address of the user
   * @param user.title - academic title of the user
   * @returns An observable that emits the server-assigned grant id
   */
  createUploadGrant(
    data: UploadGrantBase,
    user?: {
      name: string;
      email: string;
      title: string | null;
    },
  ): Observable<GrantId> {
    return this.#http.post<GrantId>(this.#grantsUrl, data).pipe(
      map((grantId) => {
        this.#invalidateGrants();
        if (user) {
          this.#addGrantLocally({
            ...data,
            id: grantId.id,
            created: new Date().toISOString(),
            user_name: user.name,
            user_email: user.email,
            user_title: user.title,
          });
        }

        return grantId;
      }),
    );
  }

  /**
   * Submit a file accession mapping for an upload box, causing it to be archived.
   * @param boxId - the ID of the upload box
   * @param request - the accession map request payload
   * @returns An observable that completes when the mapping is accepted
   */
  submitFileMapping(boxId: string, request: AccessionMapRequest): Observable<void> {
    return this.#http
      .post<void>(`${this.#boxesUrl}/${encodeURIComponent(boxId)}/file-ids`, request)
      .pipe(tap(() => this.#applyFileMappingLocally(boxId, request)));
  }

  /**
   * Apply a submitted file mapping locally: add accessions to boxFileUploads
   * and increment the box version in all local caches.
   * @param boxId - the ID of the upload box
   * @param request - the submitted accession map request
   */
  #applyFileMappingLocally(boxId: string, request: AccessionMapRequest): void {
    // Invert the mapping: boxFileId -> accession
    const accessionByBoxFileId = new Map<string, string>(
      Object.entries(request.mapping).map(([accession, boxFileId]) => [
        boxFileId,
        accession,
      ]),
    );

    const applyAccessions = (files: FileUploadWithAccession[]) =>
      files.map((f) => {
        const accession = accessionByBoxFileId.get(f.id);
        return accession !== undefined ? { ...f, accession } : f;
      });

    if (!this.boxFileUploads.error()) {
      const page = this.boxFileUploads.value();
      this.boxFileUploads.value.set({ ...page, items: applyAccessions(page.items) });
    }
    if (!this.allBoxFileUploads.error()) {
      this.allBoxFileUploads.value.set(applyAccessions(this.allBoxFileUploads.value()));
    }

    this.#updateUploadBoxLocally(boxId, { version: request.box_version });
  }

  /**
   * Send a PATCH request to set the upload box state to archived.
   * @param boxId - the ID of the upload box
   * @param currentVersion - the current (post-mapping) box version
   * @returns An observable that completes when the archive is accepted
   */
  archiveUploadBox(boxId: string, currentVersion: number): Observable<void> {
    const changes: ResearchDataUploadBoxUpdate = {
      version: currentVersion,
      state: UploadBoxState.archived,
    };
    return this.#http
      .patch<void>(`${this.#boxesUrl}/${encodeURIComponent(boxId)}`, changes)
      .pipe(tap(() => this.#updateUploadBoxLocally(boxId, changes)));
  }

  /**
   * Delete a file upload that is still being uploaded (init) or re-encrypted
   * (inbox) from an open upload box. On success, removes the file from the local
   * file list and adjusts the box file count and size so the detail view stays
   * consistent without a re-fetch.
   * @param boxId - the ID of the upload box the file belongs to
   * @param file - the file upload to delete
   * @returns An observable that completes when the file is deleted
   */
  deleteFileUpload(boxId: string, file: FileUploadWithAccession): Observable<void> {
    const url = `${this.#boxesUrl}/${encodeURIComponent(boxId)}/uploads/${encodeURIComponent(file.id)}`;
    // Any 2xx response is treated as success; HttpClient routes everything else
    // to the error channel.
    return this.#http
      .delete<void>(url)
      .pipe(tap(() => this.#deleteFileUploadLocally(boxId, file)));
  }

  /**
   * Remove a deleted file upload from local state and adjust the box file count
   * and size accordingly.
   * @param boxId - the ID of the upload box the file belonged to
   * @param file - the deleted file upload
   */
  #deleteFileUploadLocally(boxId: string, file: FileUploadWithAccession): void {
    // The file list is paginated on the server, so simply dropping the file from
    // the cached page would leave that page short and shift all following pages
    // by one, hiding a file. Refetch the affected pages instead. If the deleted
    // file was the only one on the last page, step back so the paginator does not
    // end up beyond the end of the list.
    // The cached pages must go first, otherwise both the reload and the request
    // for the previous page would just replay the responses from before the
    // deletion.
    this.#httpCache.delete(this.#fileUploadsBucket);
    const totalCount = this.boxFilesTotalCount();
    const limit = this.#fileUploadsLimit();
    const skip = this.#fileUploadsSkip();
    if (skip > 0 && skip >= totalCount - 1) {
      this.#fileUploadsSkip.set(Math.max(0, skip - limit));
    } else {
      this.boxFileUploads.reload();
    }
    this.allBoxFileUploads.reload();

    const apply = (box: ResearchDataUploadBox): ResearchDataUploadBox => ({
      ...box,
      file_count: Math.max(0, box.file_count - 1),
      size: Math.max(0, box.size - file.decrypted_size),
    });
    if (!this.uploadBox.error()) {
      const box = this.uploadBox.value();
      if (box && box.id === boxId) this.uploadBox.value.set(apply(box));
    }
    if (!this.boxRetrievalResults.error()) {
      const current = this.boxRetrievalResults.value();
      if (current.boxes.some((b) => b.id === boxId)) {
        this.boxRetrievalResults.value.set({
          count: current.count,
          boxes: current.boxes.map((b) => (b.id === boxId ? apply(b) : b)),
        });
      }
    }
  }

  /**
   * Revoke an upload grant by its ID.
   * @param id - the ID of the upload grant to revoke
   * @returns An observable that completes when the grant is revoked
   */
  revokeUploadGrant(id: string): Observable<void> {
    return this.#http.delete<void>(`${this.#grantsUrl}/${id}`).pipe(
      map((response) => {
        this.#invalidateGrants();
        try {
          this.#revokeGrantLocally(id);
        } catch {
          // ignore any errors from local state update
        }
        return response;
      }),
    );
  }
}
