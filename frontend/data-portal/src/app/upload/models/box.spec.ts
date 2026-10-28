/**
 * Test the upload box models.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { describe, expect, it } from 'vitest';
import { matchesFileStatesFilter, UploadBoxFileStatesFilter } from './box';
import { FileUploadStateCounts } from './file-upload';

/**
 * Check a condition against a box with the given state counts.
 * @param counts - the number of files per state, undefined if not provided
 * @param filter - the condition to check
 * @returns whether the condition is met
 */
function matches(
  counts: FileUploadStateCounts | undefined,
  filter: UploadBoxFileStatesFilter,
): boolean {
  const fileCount = Object.values(counts ?? {}).reduce((sum, n) => sum + n, 0);
  return matchesFileStatesFilter(
    { file_count: fileCount, file_state_counts: counts },
    filter,
  );
}

describe('matchesFileStatesFilter', () => {
  it('should match no files yet only for an empty box', () => {
    expect(matches({}, 'no_files')).toBe(true);
    expect(matchesFileStatesFilter({ file_count: 0 }, 'no_files')).toBe(true);
    expect(matchesFileStatesFilter({ file_count: 2 }, 'no_files')).toBe(false);
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
    expect(matchesFileStatesFilter({ file_count: 2 }, 'some_in_progress')).toBe(false);
    expect(matchesFileStatesFilter({ file_count: 2 }, 'all_ready')).toBe(false);
  });
});
