/**
 * Test the upload box models.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { describe, expect, it } from 'vitest';
import { matchesFileStatesFilter, UploadBoxFileStatesFilter } from './box';
import { FileUploadStateCounts } from './file-upload';

const BOX_ID = 'test-box';

/**
 * Check a condition against a box with the given state counts.
 * @param counts - the number of files per state
 * @param filter - the condition to check
 * @returns whether the condition is met
 */
function matches(
  counts: FileUploadStateCounts,
  filter: UploadBoxFileStatesFilter,
): boolean {
  const fileCount = Object.values(counts).reduce((sum, n) => sum + n, 0);
  return matchesFileStatesFilter(
    { id: BOX_ID, file_count: fileCount },
    { [BOX_ID]: counts },
    filter,
  );
}

describe('matchesFileStatesFilter', () => {
  it('should match no files yet only for an empty box', () => {
    expect(matches({}, 'no_files')).toBe(true);
    const emptyBox = { id: BOX_ID, file_count: 0 };
    const fullBox = { id: BOX_ID, file_count: 2 };
    expect(matchesFileStatesFilter(emptyBox, undefined, 'no_files')).toBe(true);
    expect(matchesFileStatesFilter(fullBox, undefined, 'no_files')).toBe(false);
  });

  it('should match all files ready only if every file is re-encrypted', () => {
    expect(matches({ interrogated: 3 }, 'all_ready')).toBe(true);
    expect(matches({ interrogated: 3, cancelled: 1 }, 'all_ready')).toBe(true);
    expect(matches({ interrogated: 3, init: 1 }, 'all_ready')).toBe(false);
    expect(matches({ archived: 3 }, 'all_ready')).toBe(false);
    expect(matches({}, 'all_ready')).toBe(false);
  });

  it('should match some files not ready if any file is in progress or failed', () => {
    expect(matches({ interrogated: 3, inbox: 1 }, 'some_not_ready')).toBe(true);
    expect(matches({ interrogated: 3, failed: 1 }, 'some_not_ready')).toBe(true);
    expect(matches({ interrogated: 3, archived: 1 }, 'some_not_ready')).toBe(false);
    expect(matches({}, 'some_not_ready')).toBe(false);
  });

  it('should match files in progress and failed files separately', () => {
    const counts = { awaiting_archival: 1, failed_interrogation: 0 };
    expect(matches(counts, 'some_in_progress')).toBe(true);
    expect(matches(counts, 'some_failed')).toBe(false);
  });

  it('should match no condition on the states without state counts', () => {
    const box = { id: BOX_ID, file_count: 2 };
    expect(matchesFileStatesFilter(box, undefined, 'some_in_progress')).toBe(false);
    expect(matchesFileStatesFilter(box, undefined, 'all_ready')).toBe(false);
  });

  it('should treat a box missing from the loaded counts as one without files', () => {
    const box = { id: BOX_ID, file_count: 0 };
    const countsByBox = { 'other-box': { interrogated: 3 } };
    expect(matchesFileStatesFilter(box, countsByBox, 'all_ready')).toBe(false);
    expect(matchesFileStatesFilter(box, countsByBox, 'some_not_ready')).toBe(false);
  });
});
