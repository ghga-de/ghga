/**
 * Tests for the UploadBoxFilesTableComponent.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { PageEvent } from '@angular/material/paginator';
import { Sort } from '@angular/material/sort';
import { UploadBoxState } from '@app/upload/models/box';
import { FileUploadWithAccession } from '@app/upload/models/file-upload';
import { screen, within } from '@testing-library/angular';
import { UploadBoxFilesTableComponent } from './upload-box-files-table';

/**
 * Create a file upload fixture.
 * @param overrides - fields to override on the default file
 * @returns a file upload with accession
 */
function makeFile(
  overrides: Partial<FileUploadWithAccession>,
): FileUploadWithAccession {
  return {
    id: 'file-1',
    box_id: 'box-1',
    alias: 'file-1.txt',
    state: 'inbox',
    state_updated: '2026-01-01T00:00:00Z',
    storage_alias: 'TUE01',
    bucket_id: 'bucket-1',
    decrypted_sha256: null,
    decrypted_size: 1024,
    encrypted_size: 2048,
    part_size: 512,
    accession: null,
    ...overrides,
  };
}

const pageFiles: FileUploadWithAccession[] = [
  makeFile({ id: 'f1', alias: 'alpha.txt', state: 'init' }),
  makeFile({ id: 'f2', alias: 'beta.txt', state: 'interrogated' }),
];

/**
 * Render the component with the given inputs.
 * @param inputs - the signal inputs to set
 * @param inputs.pageFiles - the file uploads on the page to display
 * @param inputs.boxState - the state of the box the files belong to
 * @param inputs.loading - whether the file list is still loading
 * @param inputs.showDelete - whether to show the delete column
 * @param inputs.deletable - predicate deciding which files are deletable
 * @param inputs.totalCount - the total number of files across all pages
 * @returns the created fixture
 */
async function createComponent(inputs: {
  pageFiles: FileUploadWithAccession[];
  boxState: UploadBoxState;
  loading?: boolean;
  showDelete?: boolean;
  deletable?: (file: FileUploadWithAccession) => boolean;
  totalCount?: number;
}): Promise<ComponentFixture<UploadBoxFilesTableComponent>> {
  await TestBed.configureTestingModule({
    imports: [UploadBoxFilesTableComponent],
  }).compileComponents();
  const fixture = TestBed.createComponent(UploadBoxFilesTableComponent);
  fixture.componentRef.setInput('pageFiles', inputs.pageFiles);
  fixture.componentRef.setInput('boxState', inputs.boxState);
  fixture.componentRef.setInput(
    'totalCount',
    inputs.totalCount ?? inputs.pageFiles.length,
  );
  if (inputs.loading !== undefined) {
    fixture.componentRef.setInput('loading', inputs.loading);
  }
  if (inputs.showDelete !== undefined) {
    fixture.componentRef.setInput('showDelete', inputs.showDelete);
  }
  if (inputs.deletable !== undefined) {
    fixture.componentRef.setInput('deletable', inputs.deletable);
  }
  await fixture.whenStable();
  return fixture;
}

describe('UploadBoxFilesTableComponent', () => {
  it('should render the file names', async () => {
    await createComponent({ pageFiles, boxState: UploadBoxState.open });
    expect(screen.getByText('alpha.txt')).toBeInTheDocument();
    expect(screen.getByText('beta.txt')).toBeInTheDocument();
  });

  it('should not show a delete column unless enabled', async () => {
    await createComponent({
      pageFiles,
      boxState: UploadBoxState.open,
      deletable: () => true,
    });
    expect(screen.queryByLabelText(/^Delete file/)).not.toBeInTheDocument();
  });

  it('should show delete buttons only for deletable files when enabled', async () => {
    await createComponent({
      pageFiles,
      boxState: UploadBoxState.open,
      showDelete: true,
      deletable: (file) => file.state === 'init',
    });
    expect(screen.getByLabelText('Delete file alpha.txt')).toBeInTheDocument();
    expect(screen.queryByLabelText('Delete file beta.txt')).not.toBeInTheDocument();
  });

  it('should emit deleteFile when a delete button is clicked', async () => {
    const fixture = await createComponent({
      pageFiles,
      boxState: UploadBoxState.open,
      showDelete: true,
      deletable: () => true,
    });
    const emitted: FileUploadWithAccession[] = [];
    fixture.componentInstance.deleteFile.subscribe((file) => emitted.push(file));
    screen.getByLabelText('Delete file alpha.txt').click();
    expect(emitted).toHaveLength(1);
    expect(emitted[0].alias).toBe('alpha.txt');
  });

  it('should request a new sort order instead of reordering the page itself', async () => {
    const fixture = await createComponent({
      pageFiles: [
        makeFile({ id: 'a', alias: 'gamma.txt' }),
        makeFile({ id: 'b', alias: 'alpha.txt' }),
        makeFile({ id: 'c', alias: 'beta.txt' }),
      ],
      boxState: UploadBoxState.open,
    });

    const aliasOrder = () =>
      screen
        .getAllByRole('row')
        .slice(1)
        .map((row) => within(row).getAllByRole('cell')[0].textContent?.trim());

    const sorts: Sort[] = [];
    fixture.componentInstance.sortChange.subscribe((sort) => sorts.push(sort));

    // The table is sorted by alias ascending by default, so the first click on
    // the filename header asks the server for the descending order.
    screen.getByRole('columnheader', { name: /Filename/i }).click();
    await fixture.whenStable();

    expect(sorts).toEqual([{ active: 'alias', direction: 'desc' }]);
    // The page itself is served by the backend and must stay as delivered.
    expect(aliasOrder()).toEqual(['gamma.txt', 'alpha.txt', 'beta.txt']);
  });

  it('should request a new sort order when the accession header is clicked', async () => {
    const fixture = await createComponent({
      pageFiles: [makeFile({ state: 'archived', accession: 'GHGAF001' })],
      boxState: UploadBoxState.archived,
    });

    const sorts: Sort[] = [];
    fixture.componentInstance.sortChange.subscribe((sort) => sorts.push(sort));

    screen.getByRole('columnheader', { name: /Accession/i }).click();
    await fixture.whenStable();

    expect(sorts).toEqual([{ active: 'accession', direction: 'asc' }]);
  });

  it('should hide the paginator when all files fit on one page', async () => {
    await createComponent({ pageFiles, boxState: UploadBoxState.open });
    expect(screen.queryByLabelText('Select page of files')).not.toBeInTheDocument();
  });

  it('should request another page when the paginator is used', async () => {
    const fixture = await createComponent({
      pageFiles,
      boxState: UploadBoxState.open,
      totalCount: 25,
    });
    expect(screen.getByLabelText('Select page of files')).toBeInTheDocument();

    const pages: PageEvent[] = [];
    fixture.componentInstance.page.subscribe((event) => pages.push(event));

    screen.getByLabelText('Next page').click();
    await fixture.whenStable();

    expect(pages).toHaveLength(1);
    expect(pages[0].pageIndex).toBe(1);
    expect(pages[0].pageSize).toBe(10);
  });

  it('should show a loading placeholder while the file list is loading', async () => {
    await createComponent({
      pageFiles: [],
      boxState: UploadBoxState.open,
      loading: true,
    });
    expect(screen.getByText(/loading files/i)).toBeInTheDocument();
    expect(screen.queryByText(/still empty/i)).not.toBeInTheDocument();
  });

  it('should show an empty placeholder once loaded with no files', async () => {
    await createComponent({
      pageFiles: [],
      boxState: UploadBoxState.open,
      loading: false,
    });
    expect(screen.getByText(/still empty/i)).toBeInTheDocument();
    expect(screen.queryByText(/loading files/i)).not.toBeInTheDocument();
  });

  it('should show the accession column for archived boxes', async () => {
    await createComponent({
      pageFiles: [
        makeFile({ alias: 'gamma.txt', state: 'archived', accession: 'GHGAF001' }),
      ],
      boxState: UploadBoxState.archived,
    });
    expect(screen.getByText('Accession')).toBeInTheDocument();
    expect(screen.getByText('GHGAF001')).toBeInTheDocument();
    expect(screen.queryByText('Status')).not.toBeInTheDocument();
  });
});
