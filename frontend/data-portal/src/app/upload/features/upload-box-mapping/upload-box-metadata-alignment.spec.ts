/**
 * Tests for the upload box metadata alignment component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { signal } from '@angular/core';
import { FileUploadWithAccession } from '@app/upload/models/file-upload';
import { UploadBoxService } from '@app/upload/services/upload-box';
import { render, RenderResult, screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';
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
  #allBoxFiles = signal<FileUploadWithAccession[]>(TEST_BOX_FILES);

  allBoxFileUploads = {
    isLoading: () => false,
    error: () => undefined,
  };

  allBoxFiles = this.#allBoxFiles.asReadonly();
}

/**
 * Upload a metadata file with the given content through the file picker.
 * @param container - the element the component was rendered into
 * @param text - the text content of the uploaded file
 */
async function uploadMetadata(container: Element, text: string): Promise<void> {
  const input = container.querySelector<HTMLInputElement>('input[type="file"]')!;
  const file = new File([text], 'metadata.json', { type: 'application/json' });
  await userEvent.upload(input, file);
}

describe('UploadBoxMetadataAlignmentComponent', () => {
  let result: RenderResult<UploadBoxMetadataAlignmentComponent>;
  let component: UploadBoxMetadataAlignmentComponent;

  beforeEach(async () => {
    result = await render(UploadBoxMetadataAlignmentComponent, {
      providers: [{ provide: UploadBoxService, useClass: MockUploadBoxService }],
    });
    component = result.fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
    expect(screen.getByRole('button', { name: /upload metadata file/i })).toBeVisible();
    expect(screen.queryByRole('heading', { name: 'Alignment' })).toBeNull();
  });

  it('reports alignment for a valid metadata file', async () => {
    await uploadMetadata(result.container, JSON.stringify(VALID_METADATA));

    expect(await screen.findByText('My study')).toBeVisible();
    expect(screen.getByText('metadata.json')).toBeVisible();
    expect(screen.getByRole('heading', { name: 'Alignment' })).toBeVisible();
    expect(
      screen.getByRole('button', { name: /choose a different file/i }),
    ).toBeVisible();
    expect(screen.getByText(/unmatched\.fastq\.gz/)).toBeVisible();
    expect(screen.getByText('sample-2.fastq.gz')).toBeVisible();

    expect(component.parseError()).toBeUndefined();
    expect(component.uploadedMetadata()?.study.title).toBe('My study');

    const alignment = component.alignment();
    expect(alignment?.field).toBe('name');
    expect(alignment?.matchCount).toBe(1);
    expect(alignment?.unmatchedMetadata).toEqual([
      { alias: 'alias-2', name: 'unmatched.fastq.gz' },
    ]);
    expect(alignment?.unmatchedBoxFiles.map((f) => f.id)).toEqual(['file-2']);
  });

  it('reports an error for invalid JSON', async () => {
    await uploadMetadata(result.container, '{ not json');

    expect(
      await screen.findByText('The file does not contain valid JSON.'),
    ).toBeVisible();
    expect(screen.queryByRole('heading', { name: 'Alignment' })).toBeNull();

    expect(component.uploadedMetadata()).toBeUndefined();
    expect(component.parseError()).toBe('The file does not contain valid JSON.');
  });

  it('reports an error for a metadata file with the wrong shape', async () => {
    await uploadMetadata(result.container, JSON.stringify({ studies: [] }));

    expect(
      await screen.findByRole('button', { name: /choose a different file/i }),
    ).toBeVisible();
    expect(screen.queryByRole('heading', { name: 'Alignment' })).toBeNull();

    expect(component.uploadedMetadata()).toBeUndefined();
    expect(component.parseError()).toBeDefined();
    expect(screen.getByText(component.parseError()!)).toBeVisible();
  });
});
