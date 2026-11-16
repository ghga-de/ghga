/**
 * Test the upload box priority models.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { describe, expect, it } from 'vitest';
import { UploadBoxState } from './box';
import { prioritizeBoxes, UploadBoxPriority } from './box-priority';

const { open, locked, archived } = UploadBoxState;

/**
 * Make a priority order of the given upload boxes.
 * @param boxIds - the IDs of the boxes, the highest priority first
 * @returns the priority order as returned by the RS
 */
function priorityOf(boxIds: string[]): UploadBoxPriority {
  return {
    version: 3,
    entries: boxIds.map((id) => ({
      research_data_upload_box_id: id,
      file_upload_box_id: `file-${id}`,
    })),
    changed_by: 'steward@test.dev',
    last_changed: '2025-03-01T09:00:00Z',
  };
}

/**
 * Get the IDs of upload boxes.
 * @param boxes - the upload boxes
 * @returns their IDs, in the same order
 */
function idsOf(boxes: { id: string }[]): string[] {
  return boxes.map((box) => box.id);
}

const BOXES = [
  { id: 'a', state: open, last_changed: '2025-02-01T09:00:00Z' },
  { id: 'b', state: locked, last_changed: '2025-02-02T09:00:00Z' },
  { id: 'c', state: open, last_changed: '2025-02-03T09:00:00Z' },
  { id: 'd', state: archived, last_changed: '2025-02-04T09:00:00Z' },
];

describe('prioritizeBoxes', () => {
  it('should put the boxes in list order', () => {
    expect(idsOf(prioritizeBoxes(BOXES, priorityOf(['c', 'a', 'b'])))).toEqual([
      'c',
      'a',
      'b',
    ]);
  });

  it('should ignore entries of archived boxes and of boxes that do not exist', () => {
    const priority = priorityOf(['d', 'c', 'deleted', 'a', 'b']);
    expect(idsOf(prioritizeBoxes(BOXES, priority))).toEqual(['c', 'a', 'b']);
  });

  it('should put missing boxes after the listed ones, oldest first', () => {
    const newBox = { id: 'e', state: open, last_changed: '2025-01-01T09:00:00Z' };
    const priority = priorityOf(['c']);
    expect(idsOf(prioritizeBoxes([...BOXES, newBox], priority))).toEqual([
      'c',
      'e',
      'a',
      'b',
    ]);
  });

  it('should put all boxes oldest first before the first change', () => {
    const priority: UploadBoxPriority = {
      version: 0,
      entries: [],
      changed_by: null,
      last_changed: null,
    };
    expect(idsOf(prioritizeBoxes(BOXES, priority))).toEqual(['a', 'b', 'c']);
  });
});
