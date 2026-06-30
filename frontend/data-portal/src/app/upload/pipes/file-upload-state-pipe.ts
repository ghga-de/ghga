/**
 * This pipe takes a file upload state and returns an object with the display name and text class for the specified state
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Pipe, PipeTransform } from '@angular/core';
import {
  FileUploadState,
  FileUploadStateClass,
  FileUploadStatePrintable,
} from '@app/upload/models/file-upload';

/**
 * This pipe is used to provide state-specific display names and classes for
 * file uploads.
 */
@Pipe({ name: 'FileUploadStatePipe' })
export class FileUploadStatePipe implements PipeTransform {
  /**
   * This method returns an object containing a display name and class based on
   * the file upload state provided.
   * @param state The file upload state to process
   * @returns The display name and class based on the given file upload state
   */
  transform(state: FileUploadState): { name: string; class: string } {
    return {
      name: FileUploadStatePrintable[state] ?? state,
      class: FileUploadStateClass[state] ?? 'text-warning',
    };
  }
}
