/**
 * Dialog for downloading work packages
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Clipboard } from '@angular/cdk/clipboard';
import { DatePipe } from '@angular/common';
import { Component, computed, inject, signal, viewChild } from '@angular/core';
import { apply, form, FormField } from '@angular/forms/signals';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import {
  MAT_DIALOG_DATA,
  MatDialogActions,
  MatDialogContent,
  MatDialogModule,
  MatDialogRef,
  MatDialogTitle,
} from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
// eslint-disable-next-line boundaries/element-types
import { AccessGrantWithIva } from '@app/access-requests/models/access-requests';
// eslint-disable-next-line boundaries/element-types
import { IvaTypePipe } from '@app/ivas/pipes/iva-type-pipe';
import { NotificationService } from '@app/shared/services/notification';
import { ParagraphsComponent } from '@app/shared/ui/paragraphs/paragraphs';
import { FRIENDLY_DATE_FORMAT } from '@app/shared/utils/date-formats';
import { getBackendErrorMessage, MaybeBackendError } from '@app/shared/utils/errors';
import { DatasetWithExpiration } from '@app/work-packages/models/dataset';
import { WorkPackage } from '@app/work-packages/models/work-package';
import { WorkPackageService } from '@app/work-packages/services/work-package';
import { PubkeyFieldComponent } from '@app/work-packages/ui/pubkey-input/pubkey-input';

/**
 * Dialog for creating download tokens to access datasets via the GHGA connector.
 * Collects file selection and Crypt4GH public key, validates access grant and IVA status.
 */
@Component({
  selector: 'app-download-work-package-dialog',
  imports: [
    MatButtonModule,
    MatDialogModule,
    MatDialogTitle,
    MatDialogContent,
    MatDialogActions,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatCardModule,
    ParagraphsComponent,
    DatePipe,
    IvaTypePipe,
    PubkeyFieldComponent,
    FormField,
  ],
  templateUrl: './download-work-package-dialog.html',
})
export class DownloadWorkPackageDialogComponent {
  #clipboard = inject(Clipboard);
  #dialogRef = inject(MatDialogRef<DownloadWorkPackageDialogComponent>);
  #notify = inject(NotificationService);
  #wpService = inject(WorkPackageService);
  #datasets = this.#wpService.datasets;

  protected grant = inject<AccessGrantWithIva>(MAT_DIALOG_DATA);
  protected iva = this.grant.iva;
  protected readonly friendlyDateFormat = FRIENDLY_DATE_FORMAT;

  protected datasetLoading = this.#datasets.isLoading;
  protected dataset = computed<DatasetWithExpiration | undefined>(() =>
    this.#datasets.hasValue()
      ? this.#datasets.value().find((ds) => ds.id === this.grant.dataset_id)
      : undefined,
  );

  protected model = signal({ files: '', pubkey: '' });
  protected pubkeyField = viewChild.required(PubkeyFieldComponent);
  protected downloadForm = form(this.model, (p) => {
    apply(p.pubkey, PubkeyFieldComponent.schema);
  });

  token = signal('');
  tokenIsLoading = signal(false);
  tokenError = signal('');
  tokenExpiration = signal('');

  /** Close dialog without action */
  onClose(): void {
    this.#dialogRef.close();
  }

  /**
   * Display error messages and log details when token creation fails
   * @param error Backend error to handle
   */
  #handleTokenCreationError(error: MaybeBackendError): void {
    const detail = getBackendErrorMessage(error);
    this.tokenIsLoading.set(false);

    // Error message for dialog
    let dialogMsg = 'Unfortunately, your download token could not be created';
    if (detail) dialogMsg += `: ${detail}`;
    dialogMsg += '.';
    this.tokenError.set(dialogMsg);

    // Error message for notification
    let notificationMsg = 'Cannot create download token';
    if (detail) notificationMsg += `: ${detail}`;
    notificationMsg += '!';
    this.#notify.showError(notificationMsg);

    console.debug(error);
  }

  /** Submit form to create and display a new download token */
  onCreateToken(): void {
    const dataset = this.dataset();
    if (!dataset || !this.downloadForm().valid()) return;

    const filesInput = this.model().files.trim();
    // split file IDs by comma or whitespace, and filter out empty entries
    const fileIds = filesInput.split(/[,\s]+/).filter((id) => id);

    const workPackage: WorkPackage = {
      dataset_id: dataset.id,
      // if no files have been specified, null indicates to download all
      file_ids: fileIds.length ? fileIds : null,
      type: dataset.stage,
      user_public_crypt4gh_key: this.pubkeyField().trimmedKey,
    };

    this.resetToken();
    this.tokenIsLoading.set(true);

    this.#wpService.createWorkPackage(workPackage).subscribe({
      next: ({ id, token, expires }) => {
        this.token.set(`${id}:${token}`);
        this.tokenIsLoading.set(false);
        this.tokenExpiration.set(expires);
      },
      error: (err) => this.#handleTokenCreationError(err),
    });
  }

  /**
   * Clear current token to allow creating a new one
   */
  resetToken(): void {
    this.token.set('');
    this.tokenIsLoading.set(false);
    this.tokenError.set('');
  }

  /** Copy token to clipboard and show confirmation */
  copyToken(): void {
    const token = this.token();
    if (token) {
      this.#clipboard.copy(token);
      this.#notify.showSuccess('The token has been copied to the clipboard.');
    }
  }
}
