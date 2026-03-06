/**
 * Service handling research upload boxes.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { httpResource } from '@angular/common/http';
import { computed, inject, Injectable, signal } from '@angular/core';
import { ConfigService } from '@app/shared/services/config';
import {
  BoxRetrievalResults,
  ResearchDataUploadBox,
  UploadBoxFilter,
} from '../models/box';

/**
 * Service for loading and managing upload boxes.
 */
@Injectable({ providedIn: 'root' })
export class UploadBoxService {
  #config = inject(ConfigService);
  #uosUrl = this.#config.uosUrl;
  #boxesUrl = `${this.#uosUrl}/boxes`;
  #wkvsUrl = this.#config.wkvsUrl;
  #storageLabelsUrl = `${this.#wkvsUrl}/values/storage_labels`;

  #loadAllUploadBoxes = signal<boolean>(false);
  #uploadBoxesFilter = signal<UploadBoxFilter | undefined>(undefined);

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
    () => (this.#loadAllUploadBoxes() ? this.#storageLabelsUrl : undefined),
    {
      parse: (raw) =>
        (raw as { storage_labels?: Record<string, string> }).storage_labels ?? {},
      defaultValue: {},
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
   * Current filter for upload box management.
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
      boxes = boxes.filter((box) => box.state === filter.state);
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
   * Resolve a storage alias into a human-readable storage location.
   * @param storageAlias - alias from a box item
   * @returns human-readable label or the alias itself if unknown
   */
  getStorageLocationLabel(storageAlias: string): string {
    if (this.storageLabels.error()) return storageAlias;
    return this.storageLabels.value()[storageAlias] ?? storageAlias;
  }

  /**
   * Fetch all upload boxes from the UOS backend.
   */
  loadAllUploadBoxes(): void {
    this.#loadAllUploadBoxes.set(true);
  }

  /**
   * Set a filter for upload box management.
   * @param filter - the filter to apply
   */
  setUploadBoxesFilter(filter: UploadBoxFilter): void {
    this.#uploadBoxesFilter.set(filter);
  }
}
