/**
 * Test the Upload Box File States component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { FileUploadStateCounts } from '@app/upload/models/file-upload';
import { render, screen } from '@testing-library/angular';
import { UploadBoxFileStates } from './upload-box-file-states';

/**
 * Render the component with the given inputs.
 * @param fileCount - the number of files in the box
 * @param counts - the number of files per state
 * @param loading - whether the counts are loading
 * @returns the render result
 */
function renderFileStates(
  fileCount: number,
  counts?: FileUploadStateCounts,
  loading = false,
) {
  return render(UploadBoxFileStates, { inputs: { fileCount, counts, loading } });
}

describe('UploadBoxFileStates', () => {
  it('should show only the file count without state counts', async () => {
    await renderFileStates(7);
    expect(screen.getByText('7')).toBeVisible();
    expect(screen.queryByRole('img')).toBeNull();
  });

  it('should show a placeholder for the bar while the state counts load', async () => {
    await renderFileStates(7, undefined, true);
    expect(screen.getByText('7')).toBeVisible();
    expect(screen.getByRole('img', { name: 'Loading file states' })).toBeVisible();
  });

  it('should show no placeholder for an empty box', async () => {
    await renderFileStates(0, undefined, true);
    expect(screen.queryByRole('img')).toBeNull();
  });

  it('should show the bar instead of the placeholder once the counts are there', async () => {
    await renderFileStates(2, { interrogated: 2 }, true);
    expect(screen.getByRole('img', { name: '2 ready' })).toBeVisible();
    expect(screen.queryByRole('img', { name: 'Loading file states' })).toBeNull();
  });

  it('should show a large file count on one line with thousands separators', async () => {
    await renderFileStates(100000);
    const count = screen.getByText('100,000');
    expect(count).toBeVisible();
    expect(count).toHaveClass('whitespace-nowrap');
  });

  it('should show no bar for an empty box', async () => {
    await renderFileStates(0, {});
    expect(screen.getByText('0')).toBeVisible();
    expect(screen.queryByRole('img')).toBeNull();
  });

  it('should summarise the groups of states for screen readers', async () => {
    await renderFileStates(9, {
      interrogated: 4,
      init: 1,
      inbox: 1,
      awaiting_archival: 1,
      failed: 1,
      failed_interrogation: 1,
    });
    expect(
      screen.getByRole('img', { name: '4 ready, 3 in progress, 2 failed' }),
    ).toBeVisible();
  });

  it('should draw one segment per non-empty group, sized by its count', async () => {
    const { container } = await renderFileStates(8, { archived: 6, interrogated: 2 });
    const segments = container.querySelectorAll<HTMLElement>('[role="img"] > span');
    expect(segments).toHaveLength(2);
    expect(segments[0]).toHaveClass('bg-gray-400');
    expect(segments[0].style.flexGrow).toBe('6');
    expect(segments[1]).toHaveClass('bg-success');
    expect(segments[1].style.flexGrow).toBe('2');
  });

  it('should leave deleted files out of the bar', async () => {
    await renderFileStates(2, { interrogated: 2, cancelled: 3 });
    expect(screen.getByRole('img', { name: '2 ready' })).toBeVisible();
  });

  it('should list the individual states in the tooltip without ellipses', async () => {
    await renderFileStates(3, { interrogated: 2, inbox: 1 });
    expect(screen.getByRole('img')).toHaveAccessibleDescription(
      '2 re-encrypted\n1 re-encrypting',
    );
  });

  it('should format large counts in the label and tooltip like the file count', async () => {
    await renderFileStates(171234, { interrogated: 170000, inbox: 1234 });
    const bar = screen.getByRole('img', { name: '170,000 ready, 1,234 in progress' });
    expect(bar).toHaveAccessibleDescription(
      '170,000 re-encrypted\n1,234 re-encrypting',
    );
  });

  it('should show the failed count with an icon next to the bar', async () => {
    const { container } = await renderFileStates(3, {
      interrogated: 1,
      failed_interrogation: 2,
    });
    const icon = container.querySelector('mat-icon[fontIcon="dangerous"]');
    expect(icon).toBeVisible();
    expect(icon!.parentElement).toHaveTextContent('2');
  });

  it('should not show a failed count when nothing failed', async () => {
    const { container } = await renderFileStates(2, { interrogated: 2 });
    expect(container.querySelector('mat-icon[fontIcon="dangerous"]')).toBeNull();
  });
});
