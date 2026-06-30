/**
 * Service handling studies served by the research service (rs).
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpClient, httpResource } from '@angular/common/http';
import { inject, Service, signal } from '@angular/core';
import { ConfigService } from '@app/shared/services/config';
import { Observable } from 'rxjs';
import { FileIdMap, Study } from '../models/study';

/**
 * Service for loading studies and their file mapping status from the
 * research service (rs).
 *
 * This service is used by the upload box file mapping tool to determine which
 * studies still have unmapped files and which of a study's files are unmapped.
 * File display metadata (names, aliases, formats) is obtained separately from
 * metldata, since rs does not carry filenames.
 */
@Service()
export class StudyService {
  #config = inject(ConfigService);
  #http = inject(HttpClient);
  #rsUrl = this.#config.rsUrl;
  #studiesUrl = `${this.#rsUrl}/studies`;

  #loadStudies = signal<boolean>(false);

  /**
   * Resource for loading the studies that still have unmapped files.
   * Only triggered once `loadStudies()` has been called.
   */
  studies = httpResource<Study[]>(
    () =>
      this.#loadStudies() ? `${this.#studiesUrl}?with_unmapped_files=true` : undefined,
    { defaultValue: [] },
  );

  /**
   * Trigger loading of the studies that still have unmapped files.
   */
  loadStudies(): void {
    this.#loadStudies.set(true);
  }

  /**
   * Load the file mapping status for a single study.
   *
   * The mapping tool uses this to show only the files that still need mapping:
   * a `null` value marks a file as unmapped, while a non-null value marks a file
   * that is already mapped and cannot be re-mapped (the backend only supports
   * adding new mappings, not changing existing ones).
   * @param studyId - the study ID (equal to the GHGA study accession)
   * @returns An observable emitting a map from file accession to internal file
   *   ID, where a `null` value marks a file that is still unmapped
   */
  loadFileIds(studyId: string): Observable<FileIdMap> {
    return this.#http.get<FileIdMap>(
      `${this.#studiesUrl}/${encodeURIComponent(studyId)}/file-ids`,
    );
  }
}
