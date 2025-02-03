/**
 * Work package creation page
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, inject, signal } from '@angular/core';
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
  styleUrl: './work-package.component.scss',
})
export class WorkPackageComponent {
  #wpService = inject(WorkPackageService);

  datasets = this.#wpService.datasets;
  datasetsAreLoading = this.#wpService.datasetsAreLoading;
  datasetsError = this.#wpService.datasetsError;

  selectedDataset = signal<Dataset | undefined>(undefined);

  files: string = '';
  pubKey: string = '';
  pubKeyError: string = '';

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
    // (for testing, you can use MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI=)
    let key = this.pubKey;
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
    this.pubKeyError =
      {
        1: 'Please do not paste your private key here!',
        2: 'This does not seem to be a Base64 encoded Crypt4GH key.',
      }[errorCode] ?? '';
  }

  /**
   * Submit the work package creation form
   */
  submit(): void {
    const dataset = this.selectedDataset();
    const pubKey = this.pubKeyError ? '' : this.pubKey;
    if (!dataset || !pubKey) return;
    const fileIds = (this.files || '').split(/[,\s]+/).filter((file) => file);
    const workPackage: WorkPackage = {
      dataset_id: dataset.id,
      file_ids: fileIds,
      type: dataset.stage,
      user_public_crypt4gh_key: pubKey,
    };
    console.log('Work package to be created:', workPackage);
    // TODO: call the service to create the work package, then show the created token
    // and an option to copy it (or show an error if there was a problem)
  }
}
