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
import { map, Observable, tap, throwError } from 'rxjs';
import { Iva, IvaFilter, IvaState, IvaType, UserWithIva } from '../models/iva';

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
   * Reload a given user's IVAs
   * @param userId - the user ID to load the IVAs for (default: current user)
   */
  reloadUserIvas(userId: string | undefined = undefined): void {
    if (!userId) {
      userId = this.#auth.user()?.id;
      if (!userId) return;
    }
    this.#userIvas.reload();
  }

  /**
   * Internal resource for loading the current user's IVAs
   */
  #userIvas = rxResource<Iva[], string | undefined>({
    request: this.#userId,
    loader: ({ request: userId }) => this.#http.get<Iva[]>(this.#userIvasUrl(userId)),
  });

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

  #allIvasFilter = signal<IvaFilter | undefined>(undefined);

  // signal to load all users' IVAs
  #loadAll = signal<null | undefined>(undefined);

  /**
   * Load all users' IVAs
   */
  loadAllIvas(): void {
    this.#loadAll.set(null);
  }

  /**
   * Reload all users' IVAs
   */
  reloadAllIvas(): void {
    this.#allIvas.reload();
  }

  /**
   * The current filter for the list of all IVAs
   */
  allIvasFilter = computed(
    () =>
      this.#allIvasFilter() ?? {
        name: '',
        fromDate: undefined,
        toDate: undefined,
        state: undefined,
      },
  );

  /**
   * Set a filter for the list of all IVAs
   * @param filter - the filter to apply
   */
  setAllIvasFilter(filter: IvaFilter): void {
    this.#allIvasFilter.set(
      filter.name || filter.fromDate || filter.toDate || filter.state
        ? filter
        : undefined,
    );
  }

  /**
   * Internal resource for loading all IVAs
   */
  #allIvas = rxResource<UserWithIva[], null | undefined>({
    request: this.#loadAll,
    loader: () => this.#http.get<UserWithIva[]>(this.#ivasUrl),
  });

  /**
   * The list of IVAs with corresponding user data
   */
  allIvas: Signal<UserWithIva[]> = computed(() => {
    let ivas = this.#allIvas.value() ?? [];
    const filter = this.#allIvasFilter();
    if (ivas.length && filter) {
      const name = filter.name.trim().toLowerCase();
      if (name) {
        ivas = ivas.filter((iva) => iva.user_name.toLowerCase().includes(name));
      }
      if (filter.fromDate) {
        const fromDate = filter.fromDate.toISOString();
        ivas = ivas.filter((iva) => iva.changed >= fromDate);
      }
      if (filter.toDate) {
        const toDate = filter.toDate.toISOString();
        ivas = ivas.filter((iva) => iva.changed <= toDate);
      }
      if (filter.state) {
        ivas = ivas.filter((iva) => iva.state === filter.state);
      }
    }
    return ivas;
  });

  /**
   * Whether the list of all IVAs is loading as a signal
   */
  allIvasAreLoading: Signal<boolean> = this.#allIvas.isLoading;

  /**
   * The list of all IVAs error as a signal
   */
  allIvasError: Signal<unknown> = this.#allIvas.error;

  /**
   * Add an IVA locally
   * The user name is added properly if added for the current user
   * (the UI does not allow adding IVAs for other users anyway).
   * @param opts - the options for adding the IVA
   * @param opts.id - the IVA ID
   * @param opts.type  - the IVA type
   * @param opts.value  - the IVA value
   * @param opts.userId - the user ID to crate the IVAs for
   */
  #addIvaLocally({
    id,
    type,
    value,
    userId,
  }: {
    id: string;
    type: IvaType;
    value: string;
    userId?: string;
  }): void {
    const iva: Iva = {
      id,
      type,
      value,
      state: IvaState.Unverified,
      changed: new Date().toISOString(),
    };
    this.#userIvas.value.set([...this.userIvas(), iva]);
    const user = this.#auth.user();
    const userWithIva: UserWithIva = {
      ...iva,
      user_id: userId ?? user?.id ?? '',
      user_name: user?.name ?? '',
      user_email: user?.email ?? '',
    };
    this.#allIvas.value.set([...this.allIvas(), userWithIva]);
  }

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
      .pipe(
        map(({ id }) => id),
        tap((id) => this.#addIvaLocally({ id, type, value, userId })),
      );
  }

  /**
   * Delete an IVA locally
   * @param ivaId - the ID of the IVA to delete
   */
  #deleteIvaLocally(ivaId: string): void {
    const update = <T extends { id: string }>(ivas: T[]): T[] =>
      ivas.filter((iva) => iva.id !== ivaId);

    this.#userIvas.value.set(update(this.userIvas()));
    this.#allIvas.value.set(update(this.allIvas()));
  }

  /**
   * Delete an IVA of the given user
   * and also remove it locally, so that no reload is required.
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
    return this.#http
      .delete<null>(`${this.#userIvasUrl(userId)}/${ivaId}`)
      .pipe(tap(() => this.#deleteIvaLocally(ivaId)));
  }

  #ivasRpcUrl = (ivaId: string) => `${this.#authUrl}/rpc/ivas/${ivaId}`;

  /**
   * Update the state of all IVAs locally
   * @param ivaId - the ID of the IVA to update
   * @param state - the new state of the IVA
   */
  #updateIvaStateLocally(ivaId: string, state: IvaState): void {
    const update = <T extends { id: string }>(ivas: T[]): T[] =>
      ivas.map((iva) => (iva.id === ivaId ? { ...iva, state } : iva));

    this.#userIvas.value.set(update(this.userIvas()));
    this.#allIvas.value.set(update(this.allIvas()));
  }

  /**
   * Unverify an IVA of the current user
   * and update the IVA state locally if successful.
   * @param ivaId - the ID of the IVA
   * @returns null as an observable if successful
   */
  unverifyIva(ivaId: string): Observable<null> {
    return this.#http
      .post<null>(`${this.#ivasRpcUrl(ivaId)}/unverify`, null)
      .pipe(tap(() => this.#updateIvaStateLocally(ivaId, IvaState.Unverified)));
  }

  /**
   * Request the verification of an IVA of the current user
   * and update the IVA state locally if successful.
   * @param ivaId - the ID of the IVA
   * @returns null as an observable if successful
   */
  requestCodeForIva(ivaId: string): Observable<null> {
    return this.#http
      .post<null>(`${this.#ivasRpcUrl(ivaId)}/request-code`, null)
      .pipe(tap(() => this.#updateIvaStateLocally(ivaId, IvaState.CodeRequested)));
  }

  /**
   * Create verification code for an IVA of the current user
   * and update the IVA state locally if successful.
   * @param ivaId - the ID of the IVA
   * @returns the verification code as an observable if successful
   */
  createCodeForIva(ivaId: string): Observable<string> {
    return this.#http
      .post<{
        verification_code: string;
      }>(`${this.#ivasRpcUrl(ivaId)}/create-code`, null)
      .pipe(
        map(({ verification_code }) => verification_code),
        tap(() => this.#updateIvaStateLocally(ivaId, IvaState.CodeCreated)),
      );
  }

  /**
   * Confirm verification code transmission for an IVA of the current user
   * and update the IVA state locally if successful.
   * @param ivaId - the ID of the IVA
   * @returns null as an observable if successful
   */
  confirmTransmissionForIva(ivaId: string): Observable<null> {
    return this.#http
      .post<null>(`${this.#ivasRpcUrl(ivaId)}/code-transmitted`, null)
      .pipe(tap(() => this.#updateIvaStateLocally(ivaId, IvaState.CodeTransmitted)));
  }

  /**
   * Validate verification code for an IVA of the current user
   * and update the IVA state locally if successful or too many attempts.
   * @param ivaId - the ID of the IVA
   * @param code - the verification code to be validated
   * @returns null as an observable if successfully validated,
   * if invalid, yields an error with status code 403 (Forbidden)
   * if too many attempts, yields an error with status code 429 (Too Many Requests).
   */
  validateCodeForIva(ivaId: string, code: string): Observable<null> {
    return this.#http
      .post<null>(`${this.#ivasRpcUrl(ivaId)}/validate-code`, {
        verification_code: code,
      })
      .pipe(
        tap({
          next: () => this.#updateIvaStateLocally(ivaId, IvaState.Verified),
          error: (err) => {
            if (err.status === 429) {
              this.#updateIvaStateLocally(ivaId, IvaState.Unverified);
            }
          },
        }),
      );
  }
}
