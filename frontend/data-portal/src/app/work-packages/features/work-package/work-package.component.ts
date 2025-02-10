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
import { Dataset } from '@app/work-packages/models/dataset';
import { WorkPackage } from '@app/work-packages/models/work-package';
import { WorkPackageService } from '@app/work-packages/services/work-package.service';
import { Buffer } from 'buffer';

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
  datasetsAreLoading = this.#wpService.datasetsAreLoading;
  datasetsError = this.#wpService.datasetsError;

  selectedDataset = signal<Dataset | undefined>(undefined);

  tokenAction = computed<'upload' | 'download' | 'access'>(
    () => this.selectedDataset()?.stage ?? 'access',
  );

  files = model<string>('');
  pubKey = model<string>('');
  pubKeyError = signal<string>('');

  token = signal<string>('');
  tokenIsLoading = signal<boolean>(false);
  tokenHasError = signal<boolean>(false);

  /**
   * Select a dataset
   * @param id The ID of the dataset to select
   */
  selectDataset(id: string): void {
    this.selectedDataset.set(this.datasets().find((d) => d.id === id));
  }

  /**
   * Check whether the entered public key is valid
   * and set pubKeyError accordingly.
   */
  checkPubKey(): void {
    // validate the user key
    // (for testing, you can use MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI)
    let key = this.pubKey();
    let errorCode = 0;
    if (key.match(/-.*PRIVATE.*-/)) {
      errorCode = 1; // if any kind of private key has been posted
    } else {
      // allow and trim headers and footers for public keys
      key = key.replace(/-----(BEGIN|END) CRYPT4GH PUBLIC KEY-----/, '').trim();
      // Base64 decode the key
      const binKey = Buffer.from(key, 'base64');
      if (binKey?.length !== 32) {
        // key does not have the right length for a Crypt4GH public key
        if (!Buffer.compare(binKey.subarray(0, 5), Buffer.from('c4gh-', 'ascii'))) {
          errorCode = 1; // key is actually a Base64 encoded Crypt4GH private key
        } else {
          errorCode = 2; // key is something else
        }
      }
    }
    this.pubKeyError.set(
      {
        1: 'Please do not paste your private key here!',
        2: 'This does not seem to be a Base64 encoded Crypt4GH key.',
      }[errorCode] ?? '',
    );
  }

  /**
   * Submit the work package creation form
   */
  submit(): void {
    if (this.tokenIsLoading()) return;
    const dataset = this.selectedDataset();
    const pubKey = this.pubKeyError() ? '' : this.pubKey();
    if (!dataset || !pubKey) return;
    const fileIds = (this.files() || '').split(/[,\s]+/).filter((file) => file);
    const workPackage: WorkPackage = {
      dataset_id: dataset.id,
      file_ids: fileIds,
      type: dataset.stage,
      user_public_crypt4gh_key: pubKey,
    };
    this.token.set('');
    this.tokenIsLoading.set(true);
    this.tokenHasError.set(false);
    this.#wpService.createWorkPackage(workPackage).subscribe({
      next: ({ token }) => {
        this.token.set(token);
        this.tokenIsLoading.set(false);
      },
      error: (err) => {
        this.tokenIsLoading.set(false);
        this.tokenHasError.set(true);
        this.#notify.showError(`Cannot create ${workPackage.type} token!`);
        console.debug(err);
      },
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
    this.tokenHasError.set(false);
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
