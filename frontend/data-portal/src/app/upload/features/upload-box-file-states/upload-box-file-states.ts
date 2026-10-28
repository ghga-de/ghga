/**
 * Component showing the file states of an upload box as a stacked bar.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DecimalPipe } from '@angular/common';
import { Component, computed, input } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import {
  countFileUploadStateGroup,
  FILE_UPLOAD_STATE_GROUPS,
  FileUploadStateCounts,
  FileUploadStateGroup,
  FileUploadStatePrintable,
} from '@app/upload/models/file-upload';

/** One segment of the stacked bar */
interface FileStateSegment {
  group: FileUploadStateGroup;
  label: string;
  count: number;
  barClass: string;
}

/**
 * Upload Box File States component.
 *
 * Shows the file count of an upload box next to a stacked bar with one segment
 * per group of file states, so that a list of boxes needs a single column for
 * them. The tooltip breaks the groups down into the individual states.
 */
@Component({
  selector: 'app-upload-box-file-states',
  imports: [DecimalPipe, MatIconModule, MatTooltipModule],
  templateUrl: './upload-box-file-states.html',
})
export class UploadBoxFileStates {
  /** The number of files in the box */
  fileCount = input.required<number>();

  /** The number of files per state, undefined if they are not loaded */
  counts = input<FileUploadStateCounts | undefined>();

  /** Whether the counts are loading, which shows a placeholder for the bar */
  loading = input(false);

  /** The non-empty segments of the bar, from the most to the least finished */
  protected segments = computed<FileStateSegment[]>(() => {
    const counts = this.counts();
    if (!counts) return [];
    return FILE_UPLOAD_STATE_GROUPS.map(({ group, label, barClass }) => ({
      group,
      label,
      count: countFileUploadStateGroup(counts, group),
      barClass,
    })).filter((segment) => segment.count > 0);
  });

  /** The number of failed files, shown next to the bar since a thin segment is easy to miss */
  protected failedCount = computed(
    () => this.segments().find((segment) => segment.group === 'failed')?.count ?? 0,
  );

  /** The groups as a sentence for screen readers, e.g. "38 ready, 1 failed" */
  protected summary = computed(() =>
    this.segments()
      .map((segment) => `${segment.count} ${segment.label}`)
      .join(', '),
  );

  /**
   * The individual states, one per line. The ellipsis that marks a running
   * state in the file table is dropped, since a count is not running.
   */
  protected details = computed(() => {
    const counts = this.counts();
    if (!counts) return '';
    return FILE_UPLOAD_STATE_GROUPS.flatMap((info) => info.states)
      .filter((state) => counts[state])
      .map(
        (state) =>
          `${counts[state]} ${FileUploadStatePrintable[state].replace(/…$/, '')}`,
      )
      .join('\n');
  });
}
