/**
 * Dialog for creating upload work packages.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Clipboard } from '@angular/cdk/clipboard';
import { DatePipe } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  signal,
  viewChild,
} from '@angular/core';
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
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { IvaTypePipe } from '@app/ivas/pipes/iva-type-pipe';
import { IvaService } from '@app/ivas/services/iva';
import { NotificationService } from '@app/shared/services/notification';
import { ParagraphsComponent } from '@app/shared/ui/paragraphs/paragraphs';
import { FRIENDLY_DATE_FORMAT } from '@app/shared/utils/date-formats';
import { getBackendErrorMessage, MaybeBackendError } from '@app/shared/utils/errors';
import { GrantWithBoxInfo } from '@app/upload/models/grant';
import { UploadWorkPackageRequest } from '@app/work-packages/models/work-package';
import { WorkPackageService } from '@app/work-packages/services/work-package';
import { PubkeyFieldComponent } from '@app/work-packages/ui/pubkey-input/pubkey-input';

/**
 * Dialog for creating upload tokens to upload files via the GHGA connector.
 */
@Component({
  selector: 'app-upload-work-package-dialog',
  imports: [
    MatButtonModule,
    MatDialogModule,
    MatDialogTitle,
    MatDialogContent,
    MatDialogActions,
    MatIconModule,
    MatProgressSpinnerModule,
    MatCardModule,
    ParagraphsComponent,
    DatePipe,
    IvaTypePipe,
    PubkeyFieldComponent,
    FormField,
  ],
  templateUrl: './upload-work-package-dialog.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UploadWorkPackageDialogComponent {
  #clipboard = inject(Clipboard);
  #dialogRef = inject(MatDialogRef<UploadWorkPackageDialogComponent>);
  #notify = inject(NotificationService);
  #wpService = inject(WorkPackageService);
  #iva = inject(IvaService);

  protected grant = inject<GrantWithBoxInfo>(MAT_DIALOG_DATA);
  protected iva = computed(() => {
    if (!this.grant.iva_id || this.#iva.userIvas.error()) return undefined;
    return this.#iva.userIvas.value().find((i) => i.id === this.grant.iva_id);
  });
  protected readonly friendlyDateFormat = FRIENDLY_DATE_FORMAT;

  constructor() {
    this.#iva.loadUserIvas();
  }

  protected model = signal({ pubkey: '' });
  protected pubkeyField = viewChild.required(PubkeyFieldComponent);
  protected uploadForm = form(this.model, (p) => {
    apply(p.pubkey, PubkeyFieldComponent.schema);
  });

  protected token = signal('');
  protected tokenIsLoading = signal(false);
  protected tokenError = signal('');
  protected tokenExpiration = signal('');

  /**
   * Close dialog without action.
   */
  onClose(): void {
    this.#dialogRef.close();
  }

  /**
   * Display error messages and log details when token creation fails.
   * @param error - backend error to handle
   */
  #handleTokenCreationError(error: MaybeBackendError): void {
    const detail = getBackendErrorMessage(error);
    this.tokenIsLoading.set(false);

    let dialogMsg = 'Unfortunately, your upload token could not be created';
    if (detail) dialogMsg += `: ${detail}`;
    dialogMsg += '.';
    this.tokenError.set(dialogMsg);

    let notificationMsg = 'Cannot create upload token';
    if (detail) notificationMsg += `: ${detail}`;
    notificationMsg += '!';
    this.#notify.showError(notificationMsg);

    console.debug(error);
  }

  /**
   * Submit form to create and display a new upload token.
   */
  onCreateToken(): void {
    if (!this.uploadForm().valid() || this.iva()?.state !== 'Verified') return;

    const workPackage: UploadWorkPackageRequest = {
      type: 'upload',
      research_data_upload_box_id: this.grant.box_id,
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
   * Clear current token to allow creating a new one.
   */
  resetToken(): void {
    this.token.set('');
    this.tokenIsLoading.set(false);
    this.tokenError.set('');
    this.tokenExpiration.set('');
  }

  /**
   * Copy token to clipboard and show confirmation.
   */
  copyToken(): void {
    const token = this.token();
    if (token) {
      this.#clipboard.copy(token);
      this.#notify.showSuccess('The token has been copied to the clipboard.');
    }
  }
}
