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
import { toSignal } from '@angular/core/rxjs-interop';
import {
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
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
 * Form model for creating an upload box.
 */
interface CreateUploadBoxForm {
  title: FormControl<string>;
  description: FormControl<string>;
  storage_alias: FormControl<string>;
}

/**
 * Dialog for creating a new upload box.
 */
@Component({
  selector: 'app-upload-box-creation-dialog',
  imports: [
    ReactiveFormsModule,
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

  form = new FormGroup<CreateUploadBoxForm>({
    title: new FormControl('', {
      nonNullable: true,
      validators: [Validators.required, Validators.pattern(/\S/)],
    }),
    description: new FormControl('', {
      nonNullable: true,
      validators: [Validators.required, Validators.pattern(/\S/)],
    }),
    storage_alias: new FormControl('', {
      nonNullable: true,
      validators: [Validators.required],
    }),
  });

  #formStatus = toSignal(this.form.statusChanges, { initialValue: this.form.status });

  /** Whether the submit button should be disabled. */
  isSubmitDisabled = computed(
    () => this.#formStatus() !== 'VALID' || this.isSubmitting(),
  );

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
    if (this.form.invalid || this.isSubmitting()) return;

    this.isSubmitting.set(true);
    this.creationError.set(false);

    const payload: ResearchDataUploadBoxBase = {
      title: this.form.controls.title.value.trim(),
      description: this.form.controls.description.value.trim(),
      storage_alias: this.form.controls.storage_alias.value,
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
