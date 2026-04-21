/**
 * Service handling the work packages.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpClient, httpResource } from '@angular/common/http';
import { computed, inject, Injectable } from '@angular/core';
import { AuthService } from '@app/auth/services/auth';
import { ConfigService } from '@app/shared/services/config';
import { Observable, throwError } from 'rxjs';
import { DatasetWithExpiration } from '../models/dataset';
import { WorkPackageRequest, WorkPackageResponse } from '../models/work-package';

/**
 * Work package service
 */
@Injectable({ providedIn: 'root' })
export class WorkPackageService {
  #http = inject(HttpClient);

  #config = inject(ConfigService);
  #wpsUrl = this.#config.wpsUrl;
  #usersUrl = `${this.#wpsUrl}/users`;
  #workPackagesUrl = `${this.#wpsUrl}/work-packages`;

  #auth = inject(AuthService);
  #userId = computed<string | undefined>(() => this.#auth.user()?.id || undefined);

  /**
   * Resource for loading downloadable datasets
   */
  datasets = httpResource<DatasetWithExpiration[]>(
    () => {
      const userId = this.#userId();
      return userId ? `${this.#usersUrl}/${userId}/datasets` : undefined;
    },
    {
      parse: (raw) =>
        (raw as DatasetWithExpiration[]).filter(({ stage }) => stage === 'download'),
      defaultValue: [],
    },
  ).asReadonly();

  /**
   * Check whether a work package request has a valid payload.
   * @param workPackage - work package request to validate
   * @returns true if the request is valid
   */
  #isValidWorkPackageRequest(
    workPackage: WorkPackageRequest | undefined,
  ): workPackage is WorkPackageRequest {
    if (!workPackage?.user_public_crypt4gh_key.trim()) return false;
    if (workPackage.type === 'download') return !!workPackage.dataset_id;
    return !!workPackage.research_data_upload_box_id;
  }

  /**
   * Create a work package.
   * @param workPackage - the work package request to be created
   * @returns a response with the work package ID and token
   */
  createWorkPackage(workPackage: WorkPackageRequest): Observable<WorkPackageResponse> {
    if (!this.#isValidWorkPackageRequest(workPackage)) {
      return throwError(() => new Error('Invalid work package'));
    }
    return this.#http.post<WorkPackageResponse>(this.#workPackagesUrl, workPackage);
  }
}
