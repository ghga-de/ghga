/**
 * Tests for the UploadBoxFilesTableComponent.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
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

const files: FileUploadWithAccession[] = [
  makeFile({ id: 'f1', alias: 'alpha.txt', state: 'init' }),
  makeFile({ id: 'f2', alias: 'beta.txt', state: 'interrogated' }),
];

/**
 * Render the component with the given inputs.
 * @param inputs - the signal inputs to set
 * @param inputs.files - the file uploads to display
 * @param inputs.boxState - the state of the box the files belong to
 * @param inputs.loading - whether the file list is still loading
 * @param inputs.showDelete - whether to show the delete column
 * @param inputs.deletable - predicate deciding which files are deletable
 * @returns the created fixture
 */
async function createComponent(inputs: {
  files: FileUploadWithAccession[];
  boxState: UploadBoxState;
  loading?: boolean;
  showDelete?: boolean;
  deletable?: (file: FileUploadWithAccession) => boolean;
}): Promise<ComponentFixture<UploadBoxFilesTableComponent>> {
  await TestBed.configureTestingModule({
    imports: [UploadBoxFilesTableComponent],
  }).compileComponents();
  const fixture = TestBed.createComponent(UploadBoxFilesTableComponent);
  fixture.componentRef.setInput('files', inputs.files);
  fixture.componentRef.setInput('boxState', inputs.boxState);
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
    await createComponent({ files, boxState: UploadBoxState.open });
    expect(screen.getByText('alpha.txt')).toBeInTheDocument();
    expect(screen.getByText('beta.txt')).toBeInTheDocument();
  });

  it('should not show a delete column unless enabled', async () => {
    await createComponent({
      files,
      boxState: UploadBoxState.open,
      deletable: () => true,
    });
    expect(screen.queryByLabelText(/^Delete file/)).not.toBeInTheDocument();
  });

  it('should show delete buttons only for deletable files when enabled', async () => {
    await createComponent({
      files,
      boxState: UploadBoxState.open,
      showDelete: true,
      deletable: (file) => file.state === 'init',
    });
    expect(screen.getByLabelText('Delete file alpha.txt')).toBeInTheDocument();
    expect(screen.queryByLabelText('Delete file beta.txt')).not.toBeInTheDocument();
  });

  it('should emit deleteFile when a delete button is clicked', async () => {
    const fixture = await createComponent({
      files,
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

  it('should sort the files by a column when its header is clicked', async () => {
    const fixture = await createComponent({
      files: [
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

    expect(aliasOrder()).toEqual(['gamma.txt', 'alpha.txt', 'beta.txt']);

    screen.getByRole('columnheader', { name: /Filename/i }).click();
    await fixture.whenStable();

    expect(aliasOrder()).toEqual(['alpha.txt', 'beta.txt', 'gamma.txt']);
  });

  it('should show a loading placeholder while the file list is loading', async () => {
    await createComponent({
      files: [],
      boxState: UploadBoxState.open,
      loading: true,
    });
    expect(screen.getByText(/loading files/i)).toBeInTheDocument();
    expect(screen.queryByText(/still empty/i)).not.toBeInTheDocument();
  });

  it('should show an empty placeholder once loaded with no files', async () => {
    await createComponent({
      files: [],
      boxState: UploadBoxState.open,
      loading: false,
    });
    expect(screen.getByText(/still empty/i)).toBeInTheDocument();
    expect(screen.queryByText(/loading files/i)).not.toBeInTheDocument();
  });

  it('should show the accession column for archived boxes', async () => {
    await createComponent({
      files: [
        makeFile({ alias: 'gamma.txt', state: 'archived', accession: 'GHGAF001' }),
      ],
      boxState: UploadBoxState.archived,
    });
    expect(screen.getByText('Accession')).toBeInTheDocument();
    expect(screen.getByText('GHGAF001')).toBeInTheDocument();
    expect(screen.queryByText('Status')).not.toBeInTheDocument();
  });
});
