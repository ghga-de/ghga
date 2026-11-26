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

import { ParseBytes } from '@app/shared/pipes/parse-bytes-pipe';
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
  imports: [
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatProgressBarModule,
    ParseBytes,
  ],
  templateUrl: './upload-box-metadata-alignment.html',
})
export class UploadBoxMetadataAlignment {
  #uploadBoxService = inject(UploadBoxService);

  /** The parsed and validated uploaded metadata, if any */
  uploadedMetadata = signal<UploadedMetadata | undefined>(undefined);

  /** An error describing why the last uploaded file was rejected, if any */
  parseError = signal<string | undefined>(undefined);

  /** The name of the currently loaded metadata file, if any */
  fileName = signal<string | undefined>(undefined);

  /** The size in bytes of the currently loaded metadata file, if any */
  fileSize = signal<number | undefined>(undefined);

  /**
   * Files in the upload box (excluding deleted and failed ones).
   *
   * The alignment is computed against the whole box, so this reads the complete
   * file list loaded by the parent mapping component rather than the paginated
   * one backing the file table.
   */
  boxFiles = computed<FileUploadWithAccession[]>(() =>
    this.#uploadBoxService
      .allBoxFiles()
      .filter((file) => file.state !== 'cancelled' && file.state !== 'failed'),
  );

  /** Whether upload box files are still loading */
  boxFilesLoading = computed<boolean>(() =>
    this.#uploadBoxService.allBoxFileUploads.isLoading(),
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
    this.fileSize.set(file.size);

    // Reading and parsing fail for different reasons and need different fixes,
    // so report them separately, each with the browser's own explanation.
    let text: string;
    try {
      text = await file.text();
    } catch (error) {
      this.#reject(
        `The file could not be read (${errorMessage(error)}).` +
          ' If it is still being copied or was changed, select it again.',
      );
      return;
    }
    if (!text.trim()) {
      this.#reject('The file is empty.');
      return;
    }
    let data: unknown;
    try {
      data = JSON.parse(text);
    } catch (error) {
      this.#reject(`The file does not contain valid JSON: ${errorMessage(error)}`);
      return;
    }

    const result = parseUploadedMetadata(data);
    if (!result.ok) {
      this.#reject(result.error);
      return;
    }

    this.parseError.set(undefined);
    this.uploadedMetadata.set(result.metadata);
  }

  /**
   * Drop any previously loaded metadata and show why the file was rejected.
   * @param error - the message to show
   */
  #reject(error: string): void {
    this.uploadedMetadata.set(undefined);
    this.parseError.set(error);
  }
}

/**
 * Get a readable message from a caught error.
 *
 * Checks for a message property rather than `instanceof Error`, because a
 * `DOMException` from reading the file need not be an `Error` instance.
 * @param error - the caught value
 * @returns the error's message, or its string form if it has none
 */
function errorMessage(error: unknown): string {
  if (typeof error === 'object' && error !== null && 'message' in error) {
    const { message, name } = error as { message: unknown; name?: unknown };
    if (typeof message === 'string' && message) return message;
    if (typeof name === 'string' && name) return name;
  }
  return String(error);
}
