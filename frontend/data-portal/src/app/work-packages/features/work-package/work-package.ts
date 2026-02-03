/**
 * Work package creation page
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Clipboard } from '@angular/cdk/clipboard';
import { DatePipe } from '@angular/common';
import { Component, computed, inject, model, signal, viewChild } from '@angular/core';
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
import { NotificationService } from '@app/shared/services/notification';
import { FRIENDLY_DATE_FORMAT } from '@app/shared/utils/date-formats';
import { getBackendErrorMessage, MaybeBackendError } from '@app/shared/utils/errors';
import { DatasetWithExpiration } from '@app/work-packages/models/dataset';
import { WorkPackage } from '@app/work-packages/models/work-package';
import { WorkPackageService } from '@app/work-packages/services/work-package';
import { PubkeyInputComponent } from '@app/work-packages/ui/pubkey-input/pubkey-input';

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
    DatePipe,
    PubkeyInputComponent,
  ],
  providers: [
    {
      provide: MAT_FORM_FIELD_DEFAULT_OPTIONS,
      useValue: { subscriptSizing: 'dynamic' },
    },
  ],
  templateUrl: './work-package.html',
})
export class WorkPackageComponent {
  readonly friendlyDateFormat = FRIENDLY_DATE_FORMAT;

  #clipboard = inject(Clipboard);
  #notify = inject(NotificationService);
  #wpService = inject(WorkPackageService);

  datasets = this.#wpService.datasets;

  selectedDataset = signal<DatasetWithExpiration | undefined>(undefined);

  tokenAction = computed<'upload' | 'download' | 'access'>(
    () => this.selectedDataset()?.stage ?? 'access',
  );

  files = model<string>('');

  keyInput = viewChild.required(PubkeyInputComponent);

  token = signal<string>('');
  tokenIsLoading = signal<boolean>(false);
  tokenError = signal<string>('');

  tokenExpiration = signal<string>('');

  /**
   * Select a dataset
   * @param id The ID of the dataset to select
   */
  selectDataset(id: string): void {
    this.selectedDataset.set(this.datasets.value().find((d) => d.id === id));
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
    const pubKey = this.keyInput().getTrimmedKey();
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
      next: ({ id, token, expires }) => {
        this.token.set(`${id}:${token}`);
        this.tokenIsLoading.set(false);
        this.tokenExpiration.set(expires);
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
    this.keyInput().value.set('');
    this.keyInput().error.set('');
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
