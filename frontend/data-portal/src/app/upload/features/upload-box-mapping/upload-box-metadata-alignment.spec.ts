/**
 * Tests for the upload box metadata alignment component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FileUploadWithAccession } from '@app/upload/models/file-upload';
import { UploadBoxService } from '@app/upload/services/upload-box';
import { beforeEach, describe, expect, it } from 'vitest';
import { UploadBoxMetadataAlignmentComponent } from './upload-box-metadata-alignment';

/**
 * Build a box file upload with the given id and alias.
 * @param id - the file id
 * @param alias - the file alias (filename)
 * @returns a file upload object
 */
function boxFile(id: string, alias: string): FileUploadWithAccession {
  return {
    id,
    box_id: 'box-1',
    alias,
    state: 'interrogated',
    state_updated: '2025-01-01T00:00:00Z',
    storage_alias: 'TUE01',
    bucket_id: `bucket-${id}`,
    decrypted_sha256: null,
    decrypted_size: 1024,
    encrypted_size: 1536,
    part_size: 512,
    accession: null,
  };
}

const TEST_BOX_FILES = [
  boxFile('file-1', 'sample-1.fastq.gz'),
  boxFile('file-2', 'sample-2.fastq.gz'),
];

const VALID_METADATA = {
  studies: [{ title: 'My study', description: 'A description' }],
  datasets: [],
  research_data_files: [
    {
      alias: 'alias-1',
      name: 'sample-1.fastq.gz',
      included_in_submission: true,
      dataset: 'd1',
    },
    {
      alias: 'alias-2',
      name: 'unmatched.fastq.gz',
      included_in_submission: true,
      dataset: 'd1',
    },
  ],
};

/**
 * Minimal mock of UploadBoxService for alignment component tests.
 */
class MockUploadBoxService {
  #boxFileUploads = signal<FileUploadWithAccession[]>(TEST_BOX_FILES);

  boxFileUploads = {
    value: this.#boxFileUploads.asReadonly(),
    isLoading: () => false,
    error: () => undefined,
  };
}

/**
 * Build a fake file input change event whose file resolves to the given text.
 * @param text - the text content the file should yield
 * @returns a change event usable with onFileSelected
 */
function fileEvent(text: string): Event {
  const file = {
    name: 'metadata.json',
    text: () => Promise.resolve(text),
  } as unknown as File;
  return { target: { files: [file], value: '' } } as unknown as Event;
}

describe('UploadBoxMetadataAlignmentComponent', () => {
  let component: UploadBoxMetadataAlignmentComponent;
  let fixture: ComponentFixture<UploadBoxMetadataAlignmentComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UploadBoxMetadataAlignmentComponent],
      providers: [{ provide: UploadBoxService, useClass: MockUploadBoxService }],
    }).compileComponents();

    fixture = TestBed.createComponent(UploadBoxMetadataAlignmentComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('reports alignment for a valid metadata file', async () => {
    await component.onFileSelected(fileEvent(JSON.stringify(VALID_METADATA)));

    expect(component.parseError()).toBeUndefined();
    expect(component.uploadedMetadata()?.study.title).toBe('My study');

    const result = component.alignment();
    expect(result?.field).toBe('name');
    expect(result?.matchCount).toBe(1);
    expect(result?.unmatchedMetadata).toEqual([
      { alias: 'alias-2', name: 'unmatched.fastq.gz' },
    ]);
    expect(result?.unmatchedBoxFiles.map((f) => f.id)).toEqual(['file-2']);
  });

  it('reports an error for invalid JSON', async () => {
    await component.onFileSelected(fileEvent('{ not json'));

    expect(component.uploadedMetadata()).toBeUndefined();
    expect(component.parseError()).toBe('The file does not contain valid JSON.');
  });

  it('reports an error for a metadata file with the wrong shape', async () => {
    await component.onFileSelected(fileEvent(JSON.stringify({ studies: [] })));

    expect(component.uploadedMetadata()).toBeUndefined();
    expect(component.parseError()).toBeDefined();
  });
});
