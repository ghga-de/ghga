/**
 * Tests for the metadata alignment models and logic.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { describe, expect, it } from 'vitest';
import {
  computeMetadataAlignment,
  parseUploadedMetadata,
  UploadedMetadataFile,
} from './metadata-alignment';

/**
 * Build a minimal valid metadata object with the given overrides.
 * @param overrides - properties to merge into the base object
 * @returns a metadata-shaped object
 */
function makeMetadata(overrides: Record<string, unknown> = {}): unknown {
  return {
    studies: [{ title: 'A title', description: 'A description' }],
    datasets: [],
    ...overrides,
  };
}

describe('parseUploadedMetadata', () => {
  it('rejects non-objects', () => {
    expect(parseUploadedMetadata(null).ok).toBe(false);
    expect(parseUploadedMetadata([]).ok).toBe(false);
    expect(parseUploadedMetadata('x').ok).toBe(false);
  });

  it('rejects an empty or missing studies list', () => {
    expect(parseUploadedMetadata({ datasets: [] }).ok).toBe(false);
    expect(parseUploadedMetadata({ studies: [] }).ok).toBe(false);
  });

  it('rejects studies without a title or description', () => {
    expect(parseUploadedMetadata({ studies: [{ title: 'x' }] }).ok).toBe(false);
    expect(parseUploadedMetadata({ studies: [{ description: 'x' }] }).ok).toBe(false);
  });

  it('rejects file entries missing required properties', () => {
    const result = parseUploadedMetadata(
      makeMetadata({
        research_data_files: [{ alias: 'a', name: 'b', dataset: 'd' }],
      }),
    );
    expect(result.ok).toBe(false);
  });

  it('rejects a non-boolean included_in_submission', () => {
    const result = parseUploadedMetadata(
      makeMetadata({
        research_data_files: [
          { alias: 'a', name: 'b', included_in_submission: 'true', dataset: 'd' },
        ],
      }),
    );
    expect(result.ok).toBe(false);
  });

  it('extracts the first study and allows extra properties', () => {
    const result = parseUploadedMetadata(
      makeMetadata({
        studies: [
          { title: 'First', description: 'Desc', extra: 1 },
          { title: 'Second', description: 'Other' },
        ],
      }),
    );
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.metadata.study).toEqual({
        title: 'First',
        description: 'Desc',
      });
    }
  });

  it('collects included files from all *_files lists', () => {
    const result = parseUploadedMetadata(
      makeMetadata({
        research_data_files: [
          { alias: 'a1', name: 'n1', included_in_submission: true, dataset: 'd' },
          { alias: 'a2', name: 'n2', included_in_submission: false, dataset: 'd' },
        ],
        process_data_files: [
          { alias: 'a3', name: 'n3', included_in_submission: true, dataset: 'd' },
        ],
      }),
    );
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.metadata.files).toEqual([
        { alias: 'a1', name: 'n1' },
        { alias: 'a3', name: 'n3' },
      ]);
    }
  });

  it('rejects a *_files property that is not a list', () => {
    const result = parseUploadedMetadata(makeMetadata({ research_data_files: {} }));
    expect(result.ok).toBe(false);
  });
});

const META_FILES: UploadedMetadataFile[] = [
  { alias: 'alias-1', name: 'name-1.fastq.gz' },
  { alias: 'alias-2', name: 'name-2.fastq.gz' },
  { alias: 'alias-3', name: 'name-3.fastq.gz' },
];

describe('computeMetadataAlignment', () => {
  it('prefers the field with more matches', () => {
    const boxFiles = [
      { id: 'f1', alias: 'name-1.fastq.gz' },
      { id: 'f2', alias: 'name-2.fastq.gz' },
    ];
    const result = computeMetadataAlignment(META_FILES, boxFiles);
    expect(result.field).toBe('name');
    expect(result.nameMatchCount).toBe(2);
    expect(result.aliasMatchCount).toBe(0);
    expect(result.matchCount).toBe(2);
    expect(result.unmatchedMetadata).toEqual([
      { alias: 'alias-3', name: 'name-3.fastq.gz' },
    ]);
    expect(result.unmatchedBoxFiles).toEqual([]);
  });

  it('breaks a tie in favor of the alias', () => {
    const boxFiles = [
      { id: 'f1', alias: 'alias-1' },
      { id: 'f2', alias: 'name-2.fastq.gz' },
    ];
    const result = computeMetadataAlignment(META_FILES, boxFiles);
    expect(result.aliasMatchCount).toBe(1);
    expect(result.nameMatchCount).toBe(1);
    expect(result.field).toBe('alias');
  });

  it('reports unmatched box files', () => {
    const boxFiles = [
      { id: 'f1', alias: 'alias-1' },
      { id: 'f2', alias: 'unrelated.txt' },
    ];
    const result = computeMetadataAlignment(META_FILES, boxFiles);
    expect(result.field).toBe('alias');
    expect(result.matchCount).toBe(1);
    expect(result.unmatchedBoxFiles).toEqual([{ id: 'f2', alias: 'unrelated.txt' }]);
  });

  it('matches case-insensitively when unambiguous', () => {
    const boxFiles = [{ id: 'f1', alias: 'ALIAS-1' }];
    const result = computeMetadataAlignment(META_FILES, boxFiles);
    expect(result.field).toBe('alias');
    expect(result.matchCount).toBe(1);
  });
});
