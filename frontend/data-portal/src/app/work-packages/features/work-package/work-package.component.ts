/**
 * Work package creation page
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Clipboard } from '@angular/cdk/clipboard';
import { Component, computed, inject, model, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import {
  MAT_FORM_FIELD_DEFAULT_OPTIONS,
  MatFormFieldModule,
} from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { RouterLink } from '@angular/router';
import { NotificationService } from '@app/shared/services/notification.service';
import { getBackendErrorMessage, MaybeBackendError } from '@app/shared/utils/errors';
import { Dataset } from '@app/work-packages/models/dataset';
import { WorkPackage } from '@app/work-packages/models/work-package';
import { WorkPackageService } from '@app/work-packages/services/work-package.service';

/**
 * Work package creation page component
 */
@Component({
  selector: 'app-work-package',
  imports: [
    RouterLink,
    FormsModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
  ],
  providers: [
    {
      provide: MAT_FORM_FIELD_DEFAULT_OPTIONS,
      useValue: { subscriptSizing: 'dynamic' },
    },
  ],
  templateUrl: './work-package.component.html',
})
export class WorkPackageComponent {
  #clipboard = inject(Clipboard);
  #notify = inject(NotificationService);
  #wpService = inject(WorkPackageService);

  datasets = this.#wpService.datasets;

  selectedDataset = signal<Dataset | undefined>(undefined);

  tokenAction = computed<'upload' | 'download' | 'access'>(
    () => this.selectedDataset()?.stage ?? 'access',
  );

  files = model<string>('');
  pubKey = model<string>('');
  pubKeyError = signal<string>('');

  token = signal<string>('');
  tokenIsLoading = signal<boolean>(false);
  tokenError = signal<string>('');

  /**
   * Select a dataset
   * @param id The ID of the dataset to select
   */
  selectDataset(id: string): void {
    this.selectedDataset.set(this.datasets.value().find((d) => d.id === id));
  }

  /**
   * Remove headers and fix padding of the given base64 encoded key
   * @param key - the key to be trimmed
   * @returns the trimmed key
   */
  #trimKey(key: string): string {
    // allow and trim headers and footers for public keys
    key = key
      .replace(/-----(BEGIN|END) CRYPT4GH PUBLIC KEY-----/, '')
      .replace(/^[\s-]+/, '')
      .replace(/[\s-=]+$/, '');
    const fix = key.length % 4;
    if (fix) {
      key += '='.repeat(4 - fix);
    }
    return key;
  }

  /**
   * Check whether the given key is a valid public key.
   * @param key - the key in question
   * @returns an internal error code
   */
  #checkPubKey(key: string): number {
    if (key.match(/-.*PRIVATE.*-/)) {
      return 2; // if any kind of private key has been posted
    }
    // allow and trim headers and footers for public keys
    key = this.#trimKey(key);
    if (!key) {
      return 1; // key is empty after trimming
    }
    // Base64 decode the key
    let binKey: Uint8Array;
    try {
      const binStr = atob(key);
      binKey = new Uint8Array(binStr.length);
      for (let i = 0; i < binStr.length; i++) {
        binKey[i] = binStr.charCodeAt(i);
      }
    } catch {
      return 3; // key is not a valid Base64 string
    }
    if (binKey.length !== 32) {
      // key does not have the right length for a Crypt4GH public key
      const prefix = new TextEncoder().encode('c4gh-');
      if (this.#compareUint8Arrays(binKey.subarray(0, 5), prefix)) {
        return 2; // key is actually a Base64 encoded Crypt4GH private key
      }
      return 3; // key is something else
    }
    return 0; // key seems to be ok
  }

  /**
   * Compare two Uint8Array objects for equality
   * @param arr1 - the first array
   * @param arr2 - the second array
   * @returns true if the arrays are equal, false otherwise
   */
  #compareUint8Arrays(arr1: Uint8Array, arr2: Uint8Array): boolean {
    return (
      arr1.length === arr2.length && arr1.every((value, index) => value === arr2[index])
    );
  }

  /**
   * Check whether the entered public key is valid
   * and set pubKeyError accordingly.
   */
  checkPubKey(): void {
    // validate the user key
    // (for testing, you can use MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI)
    const errorCode = this.#checkPubKey(this.pubKey());
    this.pubKeyError.set(
      {
        1: 'The key is empty.',
        2: 'Please do not paste your private key here!',
        3: 'This does not seem to be a Base64 encoded Crypt4GH key.',
      }[errorCode] ?? '',
    );
  }

  /**
   * Handle errors when creating a work package
   * @param error The error that occurred
   */
  #handleCreationError(error: MaybeBackendError): void {
    // provide detailed error message if possible
    const detail = getBackendErrorMessage(error);
    const tokenAction = this.tokenAction();
    this.tokenIsLoading.set(false);
    // message shown on the page
    let msg = `Unfortunately, your ${tokenAction} token could not be created`;
    if (detail) msg += `: ${detail}`;
    msg += '.';
    this.tokenError.set(msg);
    // message shown in the snackbar
    msg = `Cannot create ${tokenAction} token`;
    if (detail) msg += `: ${detail}`;
    msg += '!';
    this.#notify.showError(msg);
    // also log the complete error to the console
    console.debug(error);
  }

  /**
   * Submit the work package creation form
   */
  submit(): void {
    if (this.tokenIsLoading()) return;
    const dataset = this.selectedDataset();
    const pubKey = this.pubKeyError() ? '' : this.#trimKey(this.pubKey());
    if (!dataset || !pubKey) return;
    const fileIds = (this.files() || '').split(/[,\s]+/).filter((file) => file);
    const workPackage: WorkPackage = {
      dataset_id: dataset.id,
      file_ids: fileIds.length ? fileIds : null, // null means all files
      type: dataset.stage,
      user_public_crypt4gh_key: pubKey,
    };
    this.token.set('');
    this.tokenIsLoading.set(true);
    this.tokenError.set('');
    this.#wpService.createWorkPackage(workPackage).subscribe({
      next: ({ id, token }) => {
        this.token.set(`${id}:${token}`);
        this.tokenIsLoading.set(false);
      },
      error: (err) => this.#handleCreationError(err),
    });
  }

  /**
   * Reset the form to create a new work package
   */
  reset(): void {
    this.selectedDataset.set(undefined);
    this.files.set('');
    this.pubKey.set('');
    this.pubKeyError.set('');
    this.token.set('');
    this.tokenIsLoading.set(false);
    this.tokenError.set('');
  }

  /**
   * Copy the token to the clipboard
   */
  copyToken(): void {
    const token = this.token();
    if (token) {
      this.#clipboard.copy(token);
      this.#notify.showSuccess('The token has been copied to the clipboard.');
    }
  }
}
