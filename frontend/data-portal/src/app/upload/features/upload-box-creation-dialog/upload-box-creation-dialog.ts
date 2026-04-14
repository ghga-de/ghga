/**
 * Dialog component for creating an upload box.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  signal,
} from '@angular/core';
import { form, FormField, pattern, required } from '@angular/forms/signals';
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
import { ResearchDataUploadBoxBase } from '@app/upload/models/box';
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
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UploadBoxCreationDialogComponent {
  #dialogRef = inject(MatDialogRef<UploadBoxCreationDialogComponent, string>);
  #uploadBoxService = inject(UploadBoxService);
  #notificationService = inject(NotificationService);

  locationOptions = this.#uploadBoxService.uploadBoxLocationOptions;

  isSubmitting = signal(false);
  creationError = signal(false);

  protected boxModel = signal({ title: '', description: '', storage_alias: '' });

  protected boxForm = form(this.boxModel, (p) => {
    required(p.title);
    pattern(p.title, /\S/);
    required(p.description);
    pattern(p.description, /\S/);
    required(p.storage_alias);
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
    this.creationError.set(false);

    const payload: ResearchDataUploadBoxBase = {
      title: this.boxModel().title.trim(),
      description: this.boxModel().description.trim(),
      storage_alias: this.boxModel().storage_alias,
    };

    this.#uploadBoxService.createUploadBox(payload).subscribe({
      next: (id) => {
        this.#dialogRef.close(id);
      },
      error: () => {
        this.creationError.set(true);
        this.isSubmitting.set(false);
        this.#notificationService.showError(
          'Upload Box could not be created. Please try again.',
        );
      },
    });
  }
}
