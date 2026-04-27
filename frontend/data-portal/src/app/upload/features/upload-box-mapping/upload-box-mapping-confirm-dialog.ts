/**
 * Confirmation dialog for the file mapping and archive action.
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
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import {
  MAT_DIALOG_DATA,
  MatDialogActions,
  MatDialogContent,
  MatDialogModule,
  MatDialogRef,
  MatDialogTitle,
} from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';

/** Data passed into the mapping confirmation dialog */
export interface MappingConfirmDialogData {
  /** Aliases of upload-box files that are not yet mapped (must be fixed) */
  unmappedBoxFileAliases: string[];
  /** Names/aliases of metadata files that are not mapped (warning only) */
  unmappedMetaFileNames: string[];
}

/**
 * Dialog to confirm the file mapping submission and box archival.
 * Blocks submission when any upload-box files remain unmapped.
 * Shows a warning (but allows submission) when metadata files remain unmapped.
 */
@Component({
  selector: 'app-upload-box-mapping-confirm-dialog',
  imports: [
    MatButtonModule,
    MatCheckboxModule,
    MatDialogModule,
    MatDialogTitle,
    MatDialogContent,
    MatDialogActions,
    MatIconModule,
  ],
  templateUrl: './upload-box-mapping-confirm-dialog.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UploadBoxMappingConfirmDialogComponent {
  #dialogRef = inject(MatDialogRef<UploadBoxMappingConfirmDialogComponent, boolean>);
  protected data = inject<MappingConfirmDialogData>(MAT_DIALOG_DATA);

  /** Whether the user has ticked the confirmation checkbox */
  protected confirmed = signal<boolean>(false);

  /** Whether the confirm button should be enabled */
  protected canConfirm = computed<boolean>(() => this.confirmed());

  /** Close the dialog with a positive result */
  protected onConfirm(): void {
    this.#dialogRef.close(true);
  }

  /** Close the dialog with a negative result */
  protected onCancel(): void {
    this.#dialogRef.close(false);
  }
}
