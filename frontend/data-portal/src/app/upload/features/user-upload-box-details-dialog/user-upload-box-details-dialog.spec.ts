/**
 * Tests for the UserUploadBoxDetailsDialogComponent.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA } from '@angular/material/dialog';
import { ResearchDataUploadBox, UploadBoxState } from '@app/upload/models/box';
import { FileUploadWithAccession } from '@app/upload/models/file-upload';
import { GrantWithBoxInfo } from '@app/upload/models/grant';
import { UploadBoxService } from '@app/upload/services/upload-box';
import { screen } from '@testing-library/angular';
import { UserUploadBoxDetailsDialogComponent } from './user-upload-box-details-dialog';

const TIB = 1_099_511_627_776;

const box: ResearchDataUploadBox = {
  id: 'box-1',
  version: 1,
  title: 'My Box',
  description: 'My description',
  storage_alias: 'TUE01',
  max_size: 4 * TIB,
  state: UploadBoxState.locked,
  last_changed: '2026-01-01T00:00:00Z',
  changed_by: 'user-1',
  file_count: 1,
  size: 1024,
  // The underlying file upload box ID differs from the research box `id`; file
  // uploads reference this value via their own `box_id`.
  file_upload_box_id: 'file-upload-box-1',
};

const grant = { box_id: 'box-1' } as GrantWithBoxInfo;

const file: FileUploadWithAccession = {
  id: 'file-1',
  box_id: 'file-upload-box-1',
  alias: 'alpha.txt',
  state: 'interrogated',
  state_updated: '2026-01-01T00:00:00Z',
  storage_alias: 'TUE01',
  bucket_id: 'bucket-1',
  decrypted_sha256: null,
  decrypted_size: 1024,
  encrypted_size: 2048,
  part_size: 512,
  accession: null,
};

/**
 * Minimal mock of UploadBoxService for the details dialog tests.
 */
class MockUploadBoxService {
  #boxValue = signal<ResearchDataUploadBox | undefined>(undefined);
  #boxLoading = signal<boolean>(false);
  #boxError = signal<Error | undefined>(undefined);
  #files = signal<FileUploadWithAccession[]>([]);
  #filesLoading = signal<boolean>(false);

  uploadBox = {
    value: this.#boxValue.asReadonly(),
    isLoading: this.#boxLoading.asReadonly(),
    error: this.#boxError.asReadonly(),
  };

  boxFileUploads = {
    value: this.#files.asReadonly(),
    isLoading: this.#filesLoading.asReadonly(),
    error: () => undefined,
  };

  loadUploadBox = vitest.fn();
  loadFileUploadsForBox = vitest.fn();

  /**
   * Test helper: set the loaded box.
   * @param value - the box value to expose
   */
  setBox(value: ResearchDataUploadBox | undefined): void {
    this.#boxValue.set(value);
  }

  /**
   * Test helper: set an error on the box resource.
   * @param error - the error to expose
   */
  setError(error: Error): void {
    this.#boxError.set(error);
  }

  /**
   * Test helper: set the box file uploads.
   * @param files - the files to expose
   */
  setFiles(files: FileUploadWithAccession[]): void {
    this.#files.set(files);
  }

  /**
   * Test helper: set the loading state of the box file uploads.
   * @param loading - whether the file list is currently loading
   */
  setFilesLoading(loading: boolean): void {
    this.#filesLoading.set(loading);
  }
}

/**
 * Configure the testing module and create the component.
 * @returns the created fixture and the mocked service
 */
async function createComponent(): Promise<{
  fixture: ComponentFixture<UserUploadBoxDetailsDialogComponent>;
  service: MockUploadBoxService;
}> {
  await TestBed.configureTestingModule({
    imports: [UserUploadBoxDetailsDialogComponent],
    providers: [
      { provide: MAT_DIALOG_DATA, useValue: grant },
      { provide: UploadBoxService, useClass: MockUploadBoxService },
    ],
  }).compileComponents();
  const service = TestBed.inject(UploadBoxService) as unknown as MockUploadBoxService;
  const fixture = TestBed.createComponent(UserUploadBoxDetailsDialogComponent);
  return { fixture, service };
}

describe('UserUploadBoxDetailsDialogComponent', () => {
  it('should request the box when opened', async () => {
    const { fixture, service } = await createComponent();
    await fixture.whenStable();
    expect(service.loadUploadBox).toHaveBeenCalledWith('box-1');
  });

  it('should show the box details and files once loaded', async () => {
    const { fixture, service } = await createComponent();
    service.setBox(box);
    service.setFiles([file]);
    await fixture.whenStable();
    expect(screen.getByText('My Box')).toBeInTheDocument();
    expect(screen.getByText('alpha.txt')).toBeInTheDocument();
    expect(service.loadFileUploadsForBox).toHaveBeenCalledWith('box-1');
  });

  it('should not offer any modifying actions', async () => {
    const { fixture, service } = await createComponent();
    service.setBox(box);
    service.setFiles([file]);
    await fixture.whenStable();
    expect(screen.queryByLabelText(/^Delete file/)).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /edit|lock|delete|submit/i }),
    ).toBeNull();
  });

  it('should show a loading placeholder while the files are still loading', async () => {
    const { fixture, service } = await createComponent();
    service.setBox(box);
    service.setFilesLoading(true);
    await fixture.whenStable();
    expect(screen.getByText(/loading files/i)).toBeInTheDocument();
  });

  it('should show the files once loaded, not a stuck loading placeholder', async () => {
    const { fixture, service } = await createComponent();
    service.setBox(box);
    service.setFiles([file]);
    service.setFilesLoading(false);
    await fixture.whenStable();
    expect(screen.getByText('alpha.txt')).toBeInTheDocument();
    expect(screen.queryByText(/loading files/i)).not.toBeInTheDocument();
  });

  it('should show a notice when the box is empty', async () => {
    const { fixture, service } = await createComponent();
    service.setBox({ ...box, file_count: 0 });
    await fixture.whenStable();
    expect(screen.getByText(/still empty/i)).toBeInTheDocument();
  });

  it('should show an error message when loading fails', async () => {
    const { fixture, service } = await createComponent();
    service.setError(new Error('boom'));
    await fixture.whenStable();
    expect(screen.getByText(/error retrieving the upload box/i)).toBeInTheDocument();
  });
});
