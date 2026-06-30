/**
 * Dialog component for creating an upload box.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

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
import { HttpErrorResponse } from '@angular/common/http';
import { MatButtonModule } from '@angular/material/button';
import {
  MatDialogActions,
  MatDialogContent,
  MatDialogRef,
  MatDialogTitle,
} from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { NotificationService } from '@app/shared/services/notification';
import {
  BYTES_PER_TIB,
  MAX_UPLOAD_BOX_SIZE_TIB,
  MIN_UPLOAD_BOX_SIZE_TIB,
  ResearchDataUploadBoxBase,
} from '@app/upload/models/box';
import { UploadBoxService } from '@app/upload/services/upload-box';

/**
 * Dialog for creating a new upload box.
 */
@Component({
  selector: 'app-upload-box-creation-dialog',
  imports: [
    FormField,
    MatDialogTitle,
    MatDialogContent,
    MatDialogActions,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
  ],
  templateUrl: './upload-box-creation-dialog.html',
})
export class UploadBoxCreationDialogComponent {
  #dialogRef = inject(MatDialogRef<UploadBoxCreationDialogComponent, string>);
  #uploadBoxService = inject(UploadBoxService);
  #notificationService = inject(NotificationService);

  locationOptions = this.#uploadBoxService.uploadBoxLocationOptions;

  isSubmitting = signal(false);
  creationError = signal('');

  protected boxModel = signal({
    title: '',
    description: '',
    storage_alias: '',
    max_size_tb: null as number | null,
  });

  protected boxForm = form(this.boxModel, (p) => {
    required(p.title);
    pattern(p.title, /\S/);
    required(p.description);
    pattern(p.description, /\S/);
    required(p.storage_alias);
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
      return null;
    });
  });

  isSubmitDisabled = computed(() => !this.boxForm().valid() || this.isSubmitting());

  /**
   * Close the dialog without creating a box.
   */
  onCancel(): void {
    this.#dialogRef.close(undefined);
  }

  /**
   * Submit the create-upload-box request.
   */
  onSubmit(): void {
    if (!this.boxForm().valid() || this.isSubmitting()) return;

    this.isSubmitting.set(true);
    this.creationError.set('');
    const box = this.boxModel();
    const maxSizeTb = box.max_size_tb;
    if (maxSizeTb === null) {
      return;
    }

    const payload: ResearchDataUploadBoxBase = {
      title: box.title.trim(),
      description: box.description.trim(),
      storage_alias: box.storage_alias,
      max_size: Math.round(maxSizeTb * BYTES_PER_TIB),
    };

    this.#uploadBoxService.createUploadBox(payload).subscribe({
      next: (id) => {
        this.#dialogRef.close(id);
      },
      error: (err: unknown) => {
        const message =
          (err as HttpErrorResponse)?.status === 409
            ? 'An Upload Box with the same title already exists.'
            : 'Upload Box could not be created. Please try again.';
        this.creationError.set(message);
        this.isSubmitting.set(false);
        this.#notificationService.showError(message);
      },
    });
  }
}
