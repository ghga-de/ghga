/**
 * Read-only alignment check between an upload box's files and an uploaded metadata file.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, computed, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';

import { FileUploadWithAccession } from '@app/upload/models/file-upload';
import {
  computeMetadataAlignment,
  parseUploadedMetadata,
  UploadedMetadata,
} from '@app/upload/models/metadata-alignment';
import { UploadBoxService } from '@app/upload/services/upload-box';

/**
 * Embedded card that lets a data steward upload a metadata JSON file and see
 * how well the upload box files align with it, without submitting anything to
 * the backend. The alignment is reported for whichever metadata field (alias or
 * name) matches best.
 */
@Component({
  selector: 'app-upload-box-metadata-alignment',
  imports: [MatButtonModule, MatCardModule, MatIconModule, MatProgressBarModule],
  templateUrl: './upload-box-metadata-alignment.html',
})
export class UploadBoxMetadataAlignmentComponent {
  #uploadBoxService = inject(UploadBoxService);

  /** The parsed and validated uploaded metadata, if any */
  uploadedMetadata = signal<UploadedMetadata | undefined>(undefined);

  /** An error describing why the last uploaded file was rejected, if any */
  parseError = signal<string | undefined>(undefined);

  /** The name of the currently loaded metadata file, if any */
  fileName = signal<string | undefined>(undefined);

  /** Files in the upload box (excluding deleted and failed ones) */
  boxFiles = computed<FileUploadWithAccession[]>(() =>
    this.#uploadBoxService.boxFileUploads
      .value()
      .filter((file) => file.state !== 'cancelled' && file.state !== 'failed'),
  );

  /** Whether upload box files are still loading */
  boxFilesLoading = computed<boolean>(() =>
    this.#uploadBoxService.boxFileUploads.isLoading(),
  );

  /** The alignment result for the currently loaded metadata, if any */
  alignment = computed(() => {
    const metadata = this.uploadedMetadata();
    if (!metadata) return undefined;
    return computeMetadataAlignment(metadata.files, this.boxFiles());
  });

  /**
   * Read the selected file, validate it, and store the result or an error.
   * @param event - the file input change event
   */
  async onFileSelected(event: Event): Promise<void> {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    // Reset so selecting the same file again re-triggers the change event.
    input.value = '';
    if (!file) return;

    this.fileName.set(file.name);
    let data: unknown;
    try {
      data = JSON.parse(await file.text());
    } catch {
      this.uploadedMetadata.set(undefined);
      this.parseError.set('The file does not contain valid JSON.');
      return;
    }

    const result = parseUploadedMetadata(data);
    if (!result.ok) {
      this.uploadedMetadata.set(undefined);
      this.parseError.set(result.error);
      return;
    }

    this.parseError.set(undefined);
    this.uploadedMetadata.set(result.metadata);
  }
}
