/**
 * These are the unit tests for the file upload state pipe.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { FileUploadState } from '../models/file-upload';
import { FileUploadStatePipe } from './file-upload-state-pipe';

describe('FileUploadStatePipe', () => {
  it('can create an instance', () => {
    const pipe = new FileUploadStatePipe();
    expect(pipe).toBeTruthy();
  });

  it('should provide a friendly name and class for the init state', () => {
    const pipe = new FileUploadStatePipe();
    const result = pipe.transform('init');
    expect(result).toStrictEqual({ name: 'uploading…', class: 'text-warning' });
  });

  it('should provide a friendly name and class for the inbox state', () => {
    const pipe = new FileUploadStatePipe();
    const result = pipe.transform('inbox');
    expect(result).toStrictEqual({
      name: 're-encrypting…',
      class: 'text-warning',
    });
  });

  it('should provide a friendly name and class for the interrogated state', () => {
    const pipe = new FileUploadStatePipe();
    const result = pipe.transform('interrogated');
    expect(result).toStrictEqual({
      name: 're-encrypted',
      class: 'text-success',
    });
  });

  it('should provide a friendly name and class for the cancelled state', () => {
    const pipe = new FileUploadStatePipe();
    const result = pipe.transform('cancelled');
    expect(result).toStrictEqual({ name: 'deleted', class: 'text-error' });
  });

  it('should provide a friendly name and class for the archived state', () => {
    const pipe = new FileUploadStatePipe();
    const result = pipe.transform('archived');
    expect(result).toStrictEqual({ name: 'archived', class: 'text-gray-600' });
  });

  it('should fall back to the state itself for an unknown state', () => {
    const pipe = new FileUploadStatePipe();
    const result = pipe.transform('unknown' as FileUploadState);
    expect(result).toStrictEqual({ name: 'unknown', class: 'text-warning' });
  });
});
