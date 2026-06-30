/**
 * Dialog component for editing the details of an upload box.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import {
  form,
  FormField,
  max,
  min,
  pattern,
  required,
  validate,
} from '@angular/forms/signals';
import { MatButtonModule } from '@angular/material/button';
import {
  MAT_DIALOG_DATA,
  MatDialogActions,
  MatDialogContent,
  MatDialogRef,
  MatDialogTitle,
} from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { ParseBytes } from '@app/shared/pipes/parse-bytes-pipe';
import { NotificationService } from '@app/shared/services/notification';
import { getBackendErrorMessage } from '@app/shared/utils/errors';
import {
  BYTES_PER_TIB,
  MAX_UPLOAD_BOX_SIZE_TIB,
  MIN_UPLOAD_BOX_SIZE_TIB,
  ResearchDataUploadBox,
  ResearchDataUploadBoxUpdate,
  UploadBoxState,
} from '@app/upload/models/box';
import { UploadBoxService } from '@app/upload/services/upload-box';

/**
 * Dialog for editing the details (title, description, size limit) of an
 * existing upload box. The storage location is not editable and is therefore
 * not shown here (it is visible in the "Storage & Files" card). For archived
 * boxes the size limit is hidden as well, so only the title and description
 * can be corrected.
 */
@Component({
  selector: 'app-upload-box-edit-details-dialog',
  imports: [
    FormField,
    MatDialogTitle,
    MatDialogContent,
    MatDialogActions,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    ParseBytes,
  ],
  templateUrl: './upload-box-edit-details-dialog.html',
})
export class UploadBoxEditDetailsDialogComponent {
  #dialogRef = inject(MatDialogRef<UploadBoxEditDetailsDialogComponent, string>);
  #uploadBoxService = inject(UploadBoxService);
  #notificationService = inject(NotificationService);

  /** The upload box being edited, provided by the opener. */
  protected box = inject<ResearchDataUploadBox>(MAT_DIALOG_DATA);

  /** Whether the box is archived, in which case the size limit is fixed. */
  protected isArchived = this.box.state === UploadBoxState.archived;

  isSubmitting = signal(false);
  updateError = signal('');

  protected boxModel = signal({
    title: this.box.title,
    description: this.box.description,
    max_size_tb: (this.box.max_size / BYTES_PER_TIB) as number | null,
  });

  protected boxForm = form(this.boxModel, (p) => {
    required(p.title);
    pattern(p.title, /\S/);
    required(p.description);
    pattern(p.description, /\S/);
    // The size limit is fixed for archived boxes and not shown, so it is only
    // validated while the box can still accept uploads.
    if (!this.isArchived) {
      required(p.max_size_tb);
      min(p.max_size_tb, 0); // do not use actual minimum since it is also the step size
      max(p.max_size_tb, MAX_UPLOAD_BOX_SIZE_TIB);
      validate(p.max_size_tb, ({ value }) => {
        const sizeTb = value();
        if (sizeTb === null || Number.isNaN(sizeTb)) {
          return { kind: 'required' };
        }
        if (sizeTb < MIN_UPLOAD_BOX_SIZE_TIB) {
          return { kind: 'min' };
        }
        // The limit must never drop below the size already in use.
        if (sizeTb * BYTES_PER_TIB < this.box.size) {
          return { kind: 'min' };
        }
        return null;
      });
    }
  });

  /** Whether the entered size limit is below the size already used. */
  sizeBelowUsed = computed<boolean>(() => {
    if (this.isArchived) return false;
    const sizeTb = this.boxModel().max_size_tb;
    if (sizeTb === null || Number.isNaN(sizeTb)) return false;
    return sizeTb * BYTES_PER_TIB < this.box.size;
  });

  /**
   * The set of changes to send to the backend: the current version plus only
   * the fields that actually differ from the stored box. Unchanged fields are
   * excluded so the PATCH stays minimal.
   */
  changes = computed<ResearchDataUploadBoxUpdate>(() => {
    const model = this.boxModel();
    const changes: ResearchDataUploadBoxUpdate = { version: this.box.version };
    const title = model.title.trim();
    if (title !== this.box.title) {
      changes.title = title;
    }
    const description = model.description.trim();
    if (description !== this.box.description) {
      changes.description = description;
    }
    if (!this.isArchived && model.max_size_tb !== null) {
      const maxSize = Math.round(model.max_size_tb * BYTES_PER_TIB);
      if (maxSize !== this.box.max_size) {
        changes.max_size = maxSize;
      }
    }
    return changes;
  });

  /** Whether the form contains any change to be saved. */
  hasChanges = computed<boolean>(() => {
    const { title, description, max_size } = this.changes();
    return title !== undefined || description !== undefined || max_size !== undefined;
  });

  isSubmitDisabled = computed(
    () => !this.boxForm().valid() || !this.hasChanges() || this.isSubmitting(),
  );

  /**
   * Close the dialog without saving any changes.
   */
  onCancel(): void {
    this.#dialogRef.close(undefined);
  }

  /**
   * Map a failed update request to a user-facing error message.
   * @param err - the error thrown by the update request
   * @returns the message to display
   */
  #errorMessage(err: unknown): string {
    switch ((err as HttpErrorResponse)?.status) {
      case 401:
        return 'You are not authenticated. Please log in again.';
      case 403:
        return 'You are not authorized to update this upload box.';
      case 404:
        return 'The upload box could not be found. It may have been deleted.';
      case 409:
        // A 409 can mean either a duplicate title or an outdated/stale request
        // (e.g. a version conflict). The two need different advice, so the
        // duplicate-title case is detected from the backend error message.
        return /already exists|duplicate/i.test(
          getBackendErrorMessage(err as HttpErrorResponse),
        )
          ? 'An Upload Box with the same title already exists.'
          : 'The upload box was changed in the meantime or a requirement was ' +
              'not met. Please reload the page and try again.';
      case 422:
        return 'The submitted values are invalid. Please check your input.';
      default:
        return 'Upload Box could not be updated. Please try again.';
    }
  }

  /**
   * Submit the updated upload box details.
   */
  onSubmit(): void {
    if (!this.boxForm().valid() || !this.hasChanges() || this.isSubmitting()) {
      return;
    }

    this.isSubmitting.set(true);
    this.updateError.set('');

    this.#uploadBoxService.updateUploadBox(this.box.id, this.changes()).subscribe({
      next: () => {
        this.#dialogRef.close(this.box.id);
      },
      error: (err: unknown) => {
        const message = this.#errorMessage(err);
        this.updateError.set(message);
        this.isSubmitting.set(false);
        this.#notificationService.showError(message);
      },
    });
  }
}
