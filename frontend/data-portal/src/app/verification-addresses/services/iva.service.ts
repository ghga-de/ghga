/**
 * Service handling the independent verification addresses (IVAs).
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpClient } from '@angular/common/http';
import { computed, inject, Injectable, Signal, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { AuthService } from '@app/auth/services/auth.service';
import { ConfigService } from '@app/shared/services/config.service';
import { map, Observable, throwError } from 'rxjs';
import { Iva, IvaType, UserWithIva } from '../models/iva';

/**
 * IVA service
 */
@Injectable({
  providedIn: 'root',
})
export class IvaService {
  #http = inject(HttpClient);

  #config = inject(ConfigService);
  #authUrl = this.#config.authUrl;
  #usersUrl = `${this.#authUrl}/users`;

  #auth = inject(AuthService);

  #userIvasUrl = (userId: string) => `${this.#usersUrl}/${userId}/ivas`;

  // signal to load a single user's IVAs
  #userId = signal<string | undefined>(undefined);

  /**
   * Load a given user's IVAs
   * @param userId - the user ID to load the IVAs for (default: current user)
   */
  loadUserIvas(userId: string | undefined = undefined): void {
    if (!userId) {
      userId = this.#auth.user()?.id;
      if (!userId) return;
    }
    this.#userId.set(userId);
  }

  /**
   * Internal resource for loading the current user's IVAs
   */
  #userIvas = rxResource<Iva[], string | undefined>({
    request: this.#userId,
    loader: ({ request: userId }) => this.#http.get<Iva[]>(this.#userIvasUrl(userId)),
  }).asReadonly();

  /**
   * The list of IVAs of the current user
   */
  userIvas: Signal<Iva[]> = computed(() => this.#userIvas.value() ?? []);

  /**
   * Whether the list of IVAs of the currents user is loading as a signal
   */
  userIvasAreLoading: Signal<boolean> = this.#userIvas.isLoading;

  /**
   * The list of IVAs of the current user as a signal
   */
  userIvasError: Signal<unknown> = this.#userIvas.error;

  #ivasUrl = `${this.#authUrl}/ivas`;

  // signal to load all users' IVAs
  #loadAll = signal<null | undefined>(undefined);

  /**
   * Load all users' IVAs
   */
  loadAllIvas(): void {
    this.#loadAll.set(null);
  }

  /**
   * Internal resource for loading all IVAs
   */
  #allIvas = rxResource<UserWithIva[], null | undefined>({
    request: this.#loadAll,
    loader: () => this.#http.get<UserWithIva[]>(this.#ivasUrl),
  }).asReadonly();

  /**
   * The list of IVAs with corresponding user data
   */
  allIvas: Signal<UserWithIva[]> = computed(() => this.#allIvas.value() ?? []);

  /**
   * Whether the list of all IVAs is loading as a signal
   */
  allIvasAreLoading: Signal<boolean> = this.#allIvas.isLoading;

  /**
   * The list of all IVAs error as a signal
   */
  allIvasError: Signal<unknown> = this.#allIvas.error;

  /**
   * Create an IVA for the given user
   * @param opts - the options for creating the IVA
   * @param opts.type  - the IVA type
   * @param opts.value  - the IVA value
   * @param opts.userId - the user ID to crate the IVAs for (default: current user)
   * @returns the IVA ID as an observable if successful
   */
  createIva({
    type,
    value,
    userId,
  }: {
    type: IvaType;
    value: string;
    userId?: string;
  }): Observable<string> {
    if (!type || !value) {
      return throwError(() => new Error('IVA type or value missing'));
    }
    if (!userId) {
      userId = this.#auth.user()?.id;
      if (!userId) return throwError(() => new Error('Not authenticated'));
    }
    return this.#http
      .post<{ id: string }>(this.#userIvasUrl(userId), { type, value })
      .pipe(map(({ id }) => id));
  }

  /**
   * Delete an IVA of the given user
   * @param opts - the options for deleting the IVA
   * @param opts.ivaId - the IVA ID to delete
   * @param opts.userId - the user ID to crate the IVAs for (default: current user)
   * @returns a null value as an observable if successful
   */
  deleteIva({ ivaId, userId }: { ivaId: string; userId?: string }): Observable<null> {
    if (!ivaId) {
      return throwError(() => new Error('IVA ID missing'));
    }
    if (!userId) {
      userId = this.#auth.user()?.id;
      if (!userId) return throwError(() => new Error('Not authenticated'));
    }
    return this.#http.delete<null>(`${this.#userIvasUrl(userId)}/${ivaId}`);
  }

  #ivasRpcUrl = (ivaId: string) => `${this.#authUrl}/rpc/ivas/${ivaId}`;

  /**
   * Unverify an IVA of the current user
   * @param ivaId - the ID of the IVA
   * @returns null as an observable if successful
   */
  unverifyIva(ivaId: string): Observable<null> {
    return this.#http.post<null>(`${this.#ivasRpcUrl(ivaId)}/unverify`, null);
  }

  /**
   * Request the verification of an IVA of the current user
   * @param ivaId - the ID of the IVA
   * @returns null as an observable if successful
   */
  requestCodeForIva(ivaId: string): Observable<null> {
    return this.#http.post<null>(`${this.#ivasRpcUrl(ivaId)}/request-code`, null);
  }

  /**
   * Create verification code for an IVA of the current user
   * @param ivaId - the ID of the IVA
   * @returns the verification code as an observable if successful
   */
  createCodeForIva(ivaId: string): Observable<string> {
    return this.#http
      .post<{
        verification_code: string;
      }>(`${this.#ivasRpcUrl(ivaId)}/create-code`, null)
      .pipe(map(({ verification_code }) => verification_code));
  }

  /**
   * Confirm verification code transmission for an IVA of the current user
   * @param ivaId - the ID of the IVA
   * @returns null as an observable if successful
   */
  confirmTransmissionForIva(ivaId: string): Observable<null> {
    return this.#http.post<null>(`${this.#ivasRpcUrl(ivaId)}/code-transmitted`, null);
  }

  /**
   * Validate verification code for an IVA of the current user
   * @param ivaId - the ID of the IVA
   * @param code - the verification code to be validated
   * @returns null as an observable if successfully validated,
   * if invalid, yields an error with status code 403 (Forbidden)
   */
  validateCodeForIva(ivaId: string, code: string): Observable<null> {
    return this.#http.post<null>(`${this.#ivasRpcUrl(ivaId)}/validate-code`, {
      verification_code: code,
    });
  }
}
