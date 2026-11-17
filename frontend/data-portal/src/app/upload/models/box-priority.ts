/**
 * Upload box priority related models
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ResearchDataUploadBox, UploadBoxState } from './box';

/** One upload box in the priority order */
export interface UploadBoxPriorityEntry {
  research_data_upload_box_id: string;
  file_upload_box_id: string;
}

/**
 * The order in which the Data Hubs process the files of the upload boxes, as
 * returned by the RS. Before the first change, the version is 0 and the other
 * fields are empty.
 */
export interface UploadBoxPriority {
  version: number;
  /** The upload boxes in priority order, the highest priority first */
  entries: UploadBoxPriorityEntry[];
  /** The ID of the data steward who changed it last, null if the RS did */
  changed_by: string | null;
  last_changed: string | null; // ISO date string
}

/**
 * Put the upload boxes that are not archived in priority order. Entries that
 * match no box or an archived box are ignored. Boxes missing from the list come
 * after the listed ones, oldest `last_changed` first and then by ID, which is
 * where the RS puts them when it next repairs the list.
 * @param boxes - all upload boxes
 * @param priority - the priority order loaded from the RS
 * @returns the upload boxes that are not archived, the highest priority first
 */
export function prioritizeBoxes<
  Box extends Pick<ResearchDataUploadBox, 'id' | 'state' | 'last_changed'>,
>(boxes: Box[], priority: UploadBoxPriority): Box[] {
  const boxesById = new Map(
    boxes
      .filter((box) => box.state !== UploadBoxState.archived)
      .map((box) => [box.id, box]),
  );
  const listedBoxes = priority.entries.flatMap(
    (entry) => boxesById.get(entry.research_data_upload_box_id) ?? [],
  );
  const listedIds = new Set(listedBoxes.map((box) => box.id));
  const missingBoxes = [...boxesById.values()]
    .filter((box) => !listedIds.has(box.id))
    .sort(
      (a, b) =>
        a.last_changed.localeCompare(b.last_changed) || a.id.localeCompare(b.id),
    );
  return [...listedBoxes, ...missingBoxes];
}
