/**
 * Service handling the work packages.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpClient } from '@angular/common/http';
import { computed, inject, Injectable, Signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { AuthService } from '@app/auth/services/auth.service';
import { ConfigService } from '@app/shared/services/config.service';
import { map, Observable, throwError } from 'rxjs';
import { Dataset } from '../models/dataset';
import { WorkPackage, WorkPackageResponse } from '../models/work-package';

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
  #userId = computed<string | null>(() => this.#auth.user()?.id || null);

  /**
   * Internal resource for loading datasets
   */
  #datasets = rxResource<Dataset[], string | null>({
    request: this.#userId,
    loader: ({ request: userId }) => {
      if (!userId) {
        throw new Error('User not authenticated');
      }
      return (
        this.#http
          .get<Dataset[]>(`${this.#usersUrl}/${userId}/datasets`)
          // for now, this only covers downloads
          .pipe(
            map((datasets) =>
              datasets.filter(
                ({ stage }) => stage === 'upload' || stage === 'download',
              ),
            ),
          )
      );
    },
  }).asReadonly();

  /**
   * The list of datasets belonging to the logged in user
   */
  datasets: Signal<Dataset[]> = computed(() => this.#datasets.value() ?? []);

  /**
   * Whether the datasets list is loading as a signal
   */
  datasetsAreLoading: Signal<boolean> = this.#datasets.isLoading;

  /**
   * The dataset list error as a signal
   */
  datasetsError: Signal<unknown> = this.#datasets.error;

  /**
   * Create a work package for download
   * @param workPackage - the work package to be created
   * @returns a response with the work package id and the download token
   */
  createWorkPackage(workPackage: WorkPackage): Observable<WorkPackageResponse> {
    if (
      !workPackage ||
      workPackage.type !== 'download' ||
      !workPackage.user_public_crypt4gh_key
    ) {
      // do not throw immediately to unify error handling
      return throwError(() => new Error('Invalid work package'));
    }
    return this.#http.post<WorkPackageResponse>(this.#workPackagesUrl, workPackage);
  }
}
