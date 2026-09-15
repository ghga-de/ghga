/**
 * Tests for the upload box manager detail component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { computed, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialog } from '@angular/material/dialog';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { uploadBox1FileUploads, uploadBoxes, uploadGrants } from '@app/../mocks/data';
import { fakeActivatedRoute } from '@app/../mocks/route';
import { UserService } from '@app/auth/services/user';
import { MetadataService } from '@app/metadata/services/metadata';
import { NavigationTrackingService } from '@app/shared/services/navigation';
import { NotificationService } from '@app/shared/services/notification';
import { ResearchDataUploadBox, UploadBoxState } from '@app/upload/models/box';
import {
  DEFAULT_UPLOADS_PAGE_SIZE,
  FileUploadWithAccession,
} from '@app/upload/models/file-upload';
import { UploadGrant } from '@app/upload/models/grant';
import { StudyService } from '@app/upload/services/study';
import { UploadBoxService } from '@app/upload/services/upload-box';
import { screen } from '@testing-library/angular';
import { of, throwError } from 'rxjs';
import { UploadBoxMappingComponent } from '../upload-box-mapping/upload-box-mapping';
import { UploadBoxManagerDetailComponent } from './upload-box-manager-detail';

const TEST_BOX = uploadBoxes.boxes[0];

/**
 * Minimal mock of UploadBoxService for detail component tests.
 */
class MockUploadBoxService {
  #uploadBoxes = signal<ResearchDataUploadBox[]>([]);
  #singleBoxError = signal<Error | undefined>(undefined);
  #singleBoxValue = signal<ResearchDataUploadBox | undefined>(undefined);
  #singleBoxLoading = signal<boolean>(false);
  #boxGrantsList = signal<UploadGrant[]>([]);
  #fileUploadsList = signal<FileUploadWithAccession[]>([]);

  uploadBox = {
    value: this.#singleBoxValue.asReadonly(),
    isLoading: this.#singleBoxLoading.asReadonly(),
    error: this.#singleBoxError.asReadonly(),
  };

  uploadBoxes = this.#uploadBoxes.asReadonly();

  boxGrants = {
    value: this.#boxGrantsList.asReadonly(),
    isLoading: () => false,
    error: () => undefined,
  };

  boxFileUploads = {
    isLoading: () => false,
    error: () => undefined,
  };

  allBoxFileUploads = {
    isLoading: () => false,
    error: () => undefined,
  };

  boxFiles = this.#fileUploadsList.asReadonly();
  boxFilesTotalCount = computed<number>(() => this.#fileUploadsList().length);
  boxFilesSkip = signal<number>(0);
  boxFilesLimit = signal<number>(DEFAULT_UPLOADS_PAGE_SIZE);
  boxFilesSortState = signal({ column: 'alias', direction: 'asc' as const });

  allBoxFiles = this.#fileUploadsList.asReadonly();

  storageLabels = {
    value: () => ({ TUE01: 'Tübingen 1' }) as Record<string, string>,
    error: () => undefined,
  };

  loadUploadBox = vitest.fn();
  reloadUploadBox = vitest.fn();
  loadStorageLabels = vitest.fn();
  loadBoxGrants = vitest.fn();
  reloadBoxGrants = vitest.fn();
  loadFileUploadsForBox = vitest.fn();
  reloadFileUploadsForBox = vitest.fn();
  loadAllFileUploadsForBox = vitest.fn();
  paginateFileUploads = vitest.fn();
  sortFileUploadsByColumn = vitest.fn();
  addUploadGrant = vitest.fn();
  submitFileMapping = vitest.fn(() => of(undefined));
  archiveUploadBox = vitest.fn(() => of(undefined));
  deleteFileUpload = vitest.fn(() => of(undefined));
  requeueFileUpload = vitest.fn(() => of(undefined));
  requeueAllFileUploads = vitest.fn(() =>
    of({ requeued: [] as string[], skipped: [] as string[] }),
  );
  lockUploadBox = vitest.fn(() => of(undefined));
  openUploadBox = vitest.fn(() => of(undefined));
  deleteUploadBox = vitest.fn(() => of(undefined));

  getStorageLocationLabel = (alias: string) =>
    this.storageLabels.value()[alias] ?? alias;

  /**
   * Set up the service with boxes in the list.
   * @param boxes - upload boxes to expose
   */
  setUploadBoxes(boxes: ResearchDataUploadBox[]): void {
    this.#uploadBoxes.set(boxes);
  }

  /**
   * Set up the service with a single fetched box.
   * @param box - the single box value
   */
  setSingleBox(box: ResearchDataUploadBox | undefined): void {
    this.#singleBoxValue.set(box);
  }

  /**
   * Set a fetch error for the single box resource.
   * @param error - the error to expose
   */
  setSingleBoxError(error: Error | undefined): void {
    this.#singleBoxError.set(error);
  }

  /**
   * Set loading state for the single box resource.
   * @param loading - whether loading is in progress
   */
  setSingleBoxLoading(loading: boolean): void {
    this.#singleBoxLoading.set(loading);
  }

  /**
   * Set upload grants for the box grants resource.
   * @param grants - the grants to expose
   */
  setBoxGrants(grants: UploadGrant[]): void {
    this.#boxGrantsList.set(grants);
  }

  /**
   * Set the file uploads for the box file uploads resource.
   * @param files - the file uploads to expose
   */
  setFileUploads(files: FileUploadWithAccession[]): void {
    this.#fileUploadsList.set(files);
  }
}

/**
 * Minimal mock of StudyService for the embedded mapping component.
 */
class MockStudyService {
  studies = {
    value: () => [],
    isLoading: () => false,
    error: () => undefined,
  };

  loadStudies = vitest.fn();
  loadFileIds = vitest.fn(() => of({}));
}

/**
 * Minimal mock of MetadataService for the embedded mapping component.
 */
class MockMetadataService {
  filesOfStudyId = vitest.fn(() => of([]));
}

const mockDialog = { open: vitest.fn() };

/**
 * Minimal mock of UserService for detail component tests.
 */
class MockUserService {
  /**
   * Returns a stub user resource that never loads.
   * @returns a stub user resource
   */
  createUserFetcher() {
    return {
      load: vitest.fn(),
      resource: {
        isLoading: () => false,
        error: () => undefined,
        value: () => undefined,
      },
    };
  }
}

const mockNavigationService = { back: vitest.fn() };
const mockNotificationService = {
  showError: vitest.fn(),
  showInfo: vitest.fn(),
  showSuccess: vitest.fn(),
  showWarning: vitest.fn(),
};

describe('UploadBoxManagerDetailComponent', () => {
  let component: UploadBoxManagerDetailComponent;
  let fixture: ComponentFixture<UploadBoxManagerDetailComponent>;
  let uploadBoxService: MockUploadBoxService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UploadBoxManagerDetailComponent],
      providers: [
        provideRouter([]),
        { provide: UploadBoxService, useClass: MockUploadBoxService },
        { provide: UserService, useClass: MockUserService },
        { provide: NavigationTrackingService, useValue: mockNavigationService },
        { provide: NotificationService, useValue: mockNotificationService },
        { provide: ActivatedRoute, useValue: fakeActivatedRoute },
        { provide: StudyService, useClass: MockStudyService },
        { provide: MatDialog, useValue: mockDialog },
      ],
    })
      .overrideComponent(UploadBoxMappingComponent, {
        set: {
          providers: [{ provide: MetadataService, useClass: MockMetadataService }],
        },
      })
      .compileComponents();

    uploadBoxService = TestBed.inject(
      UploadBoxService,
    ) as unknown as MockUploadBoxService;
    fixture = TestBed.createComponent(UploadBoxManagerDetailComponent);
    component = fixture.componentInstance;
  });

  describe('when box is in the list cache', () => {
    beforeEach(async () => {
      uploadBoxService.setUploadBoxes(uploadBoxes.boxes);
      fixture.componentRef.setInput('id', TEST_BOX.id);
      await fixture.whenStable();
    });

    it('should show the heading', () => {
      const heading = screen.getByRole('heading', { level: 1 });
      expect(heading).toHaveTextContent('Upload Box Details');
    });

    it('should display the box title', () => {
      expect(screen.getByText(TEST_BOX.title)).toBeVisible();
    });

    it('should display the storage location label', () => {
      expect(screen.getByText('Tübingen 1')).toBeVisible();
    });

    it('should call reloadUploadBox to keep detail state synchronized', () => {
      expect(uploadBoxService.reloadUploadBox).toHaveBeenCalledWith(TEST_BOX.id);
    });

    it('should call reloadBoxGrants with the box id', () => {
      expect(uploadBoxService.reloadBoxGrants).toHaveBeenCalledWith(TEST_BOX.id);
    });

    it('should fetch the box, its grants and its files again when the refresh button is used', () => {
      screen.getByRole('button', { name: 'Refresh the upload box details' }).click();
      expect(uploadBoxService.reloadUploadBox).toHaveBeenLastCalledWith(TEST_BOX.id);
      expect(uploadBoxService.reloadBoxGrants).toHaveBeenLastCalledWith(TEST_BOX.id);
      expect(uploadBoxService.reloadFileUploadsForBox).toHaveBeenLastCalledWith(
        TEST_BOX.id,
      );
    });

    it('should display upload grants when available', async () => {
      uploadBoxService.setBoxGrants(uploadGrants);
      await fixture.whenStable();
      expect(screen.getAllByText('John Doe (doe@home.org)')).toHaveLength(3);
    });

    it('should mark a grant as active while today is within its validity period', async () => {
      // Bounds far in the past/future keep the outcome independent of the clock.
      uploadBoxService.setBoxGrants([
        { ...uploadGrants[0], valid_from: '2000-01-01', valid_until: '2999-12-31' },
      ]);
      await fixture.whenStable();
      const status = screen.getByText('active');
      expect(status).toBeVisible();
      expect(status).toHaveClass('text-success');
    });

    it('should mark a grant as inactive once its validity period has passed', async () => {
      uploadBoxService.setBoxGrants([
        { ...uploadGrants[0], valid_from: '2000-01-01', valid_until: '2000-12-31' },
      ]);
      await fixture.whenStable();
      const status = screen.getByText('inactive');
      expect(status).toBeVisible();
      expect(status).toHaveClass('text-error');
    });

    it('should show "No upload grants found" when grants list is empty', () => {
      expect(screen.getByText(/no upload grants found/i)).toBeVisible();
    });
  });

  describe('when box is not in cache and must be fetched', () => {
    beforeEach(async () => {
      // Empty list — forces individual fetch
      uploadBoxService.setUploadBoxes([]);
      fixture.componentRef.setInput('id', TEST_BOX.id);
      await fixture.whenStable();
    });

    it('should call reloadUploadBox with the correct id', () => {
      expect(uploadBoxService.reloadUploadBox).toHaveBeenCalledWith(TEST_BOX.id);
    });

    it('should show loading indicator while fetching', async () => {
      uploadBoxService.setSingleBoxLoading(true);
      await fixture.whenStable();
      expect(screen.getByText(/loading upload box details/i)).toBeVisible();
    });

    it('should display the box once fetched', async () => {
      uploadBoxService.setSingleBox(TEST_BOX);
      await fixture.whenStable();
      expect(screen.getByText(TEST_BOX.title)).toBeVisible();
    });
  });

  describe('when the box is not found', () => {
    beforeEach(async () => {
      uploadBoxService.setUploadBoxes([]);
      const notFound = Object.assign(new Error('Not Found'), { status: 404 });
      uploadBoxService.setSingleBoxError(notFound);
      fixture.componentRef.setInput('id', 'nonexistent-id');
      await fixture.whenStable();
    });

    it('should show a not-found message', () => {
      expect(screen.getByText(/upload box not found/i)).toBeVisible();
    });
  });

  describe('when there is a server error', () => {
    beforeEach(async () => {
      uploadBoxService.setUploadBoxes([]);
      const serverError = Object.assign(new Error('Server Error'), { status: 500 });
      uploadBoxService.setSingleBoxError(serverError);
      fixture.componentRef.setInput('id', TEST_BOX.id);
      await fixture.whenStable();
    });

    it('should show a generic error message', () => {
      expect(screen.getByText(/error retrieving the upload box/i)).toBeVisible();
    });
  });

  describe('when box state is locked', () => {
    beforeEach(async () => {
      const lockedBox: ResearchDataUploadBox = {
        ...TEST_BOX,
        state: UploadBoxState.locked,
      };
      uploadBoxService.setUploadBoxes([lockedBox]);
      fixture.componentRef.setInput('id', lockedBox.id);
      await fixture.whenStable();
    });

    it('should render the file mapping card', () => {
      expect(screen.getByRole('heading', { name: /study/i })).toBeVisible();
    });
  });

  describe('onBoxArchived()', () => {
    beforeEach(async () => {
      uploadBoxService.setUploadBoxes(uploadBoxes.boxes);
      fixture.componentRef.setInput('id', TEST_BOX.id);
      await fixture.whenStable();
    });

    it('should reload the upload box after archival', () => {
      const callsBefore = (
        uploadBoxService.loadUploadBox as ReturnType<typeof vitest.fn>
      ).mock.calls.length;
      component.onBoxArchived();
      expect(uploadBoxService.loadUploadBox).toHaveBeenCalledTimes(callsBefore + 1);
      expect(uploadBoxService.loadUploadBox).toHaveBeenLastCalledWith(TEST_BOX.id);
    });
  });

  describe('deleting a file', () => {
    const initFile = uploadBox1FileUploads.find((file) => file.state === 'init')!;
    const interrogatedFile = uploadBox1FileUploads.find(
      (file) => file.state === 'interrogated',
    )!;

    beforeEach(async () => {
      mockDialog.open.mockReset();
      mockNotificationService.showSuccess.mockClear();
      mockNotificationService.showError.mockClear();
      uploadBoxService.deleteFileUpload.mockClear();
      uploadBoxService.deleteFileUpload.mockReturnValue(of(undefined));

      uploadBoxService.setUploadBoxes(uploadBoxes.boxes);
      uploadBoxService.setFileUploads(uploadBox1FileUploads);
      fixture.componentRef.setInput('id', TEST_BOX.id);
      await fixture.whenStable();
    });

    it('should show a delete button for deletable files in an open box', () => {
      expect(
        screen.getByLabelText(`Delete file ${initFile.alias}`),
      ).toBeInTheDocument();
    });

    it('should allow deleting a file that failed re-encryption in an open box', () => {
      expect(
        component.canDeleteFile({ ...interrogatedFile, state: 'failed_interrogation' }),
      ).toBe(true);
    });

    it('should delete an init file directly without confirmation', async () => {
      component.deleteFile(initFile);
      await fixture.whenStable();

      expect(mockDialog.open).not.toHaveBeenCalled();
      expect(uploadBoxService.deleteFileUpload).toHaveBeenCalledWith(
        TEST_BOX.id,
        initFile,
      );
      expect(mockNotificationService.showSuccess).toHaveBeenCalled();
      expect(mockNotificationService.showError).not.toHaveBeenCalled();
    });

    it('should escape the file name in the deletion confirmation', async () => {
      mockDialog.open.mockReturnValue({ afterClosed: () => of(false) });

      component.deleteFile({ ...interrogatedFile, alias: '<i>x</i>.bam' });
      await fixture.whenStable();

      const { message } = mockDialog.open.mock.calls[0][1].data;
      expect(message).toContain('<strong>&lt;i&gt;x&lt;/i&gt;.bam</strong>');
    });

    it('should ask for confirmation and delete on confirm for a re-encrypted file', async () => {
      mockDialog.open.mockReturnValue({ afterClosed: () => of(true) });

      component.deleteFile(interrogatedFile);
      await fixture.whenStable();

      expect(mockDialog.open).toHaveBeenCalledTimes(1);
      expect(uploadBoxService.deleteFileUpload).toHaveBeenCalledWith(
        TEST_BOX.id,
        interrogatedFile,
      );
      expect(mockNotificationService.showSuccess).toHaveBeenCalled();
    });

    it('should not delete when the confirmation is cancelled', async () => {
      mockDialog.open.mockReturnValue({ afterClosed: () => of(false) });

      component.deleteFile(interrogatedFile);
      await fixture.whenStable();

      expect(mockDialog.open).toHaveBeenCalledTimes(1);
      expect(uploadBoxService.deleteFileUpload).not.toHaveBeenCalled();
      expect(mockNotificationService.showSuccess).not.toHaveBeenCalled();
    });

    it('should show an error notification when deletion fails', async () => {
      uploadBoxService.deleteFileUpload.mockReturnValueOnce(
        throwError(() => new Error('failed')),
      );

      component.deleteFile(initFile);
      await fixture.whenStable();

      expect(mockNotificationService.showError).toHaveBeenCalled();
      expect(mockNotificationService.showSuccess).not.toHaveBeenCalled();
    });
  });

  describe('requeueing files', () => {
    const failedFile: FileUploadWithAccession = {
      ...uploadBox1FileUploads[0],
      id: 'failed-file',
      alias: 'failed.fastq.gz',
      state: 'failed_interrogation',
    };
    const lockedBox: ResearchDataUploadBox = {
      ...TEST_BOX,
      state: UploadBoxState.locked,
    };

    beforeEach(async () => {
      mockDialog.open.mockReset();
      mockDialog.open.mockReturnValue({ afterClosed: () => of(true) });
      Object.values(mockNotificationService).forEach((fn) => fn.mockClear());
      uploadBoxService.requeueFileUpload.mockClear();
      uploadBoxService.requeueFileUpload.mockReturnValue(of(undefined));
      uploadBoxService.requeueAllFileUploads.mockClear();

      uploadBoxService.setUploadBoxes([lockedBox]);
      uploadBoxService.setFileUploads([uploadBox1FileUploads[0], failedFile]);
      fixture.componentRef.setInput('id', lockedBox.id);
      await fixture.whenStable();
      uploadBoxService.reloadUploadBox.mockClear();
    });

    it('should offer a retry only for files that failed re-encryption', () => {
      expect(
        screen.getByLabelText('Retry re-encryption of failed.fastq.gz'),
      ).toBeInTheDocument();
      expect(
        screen.queryByLabelText(
          `Retry re-encryption of ${uploadBox1FileUploads[0].alias}`,
        ),
      ).not.toBeInTheDocument();
    });

    it('should not allow deleting a file that failed re-encryption while the box is locked', () => {
      expect(component.canDeleteFile(failedFile)).toBe(false);
    });

    it('should requeue a file after confirmation', async () => {
      component.requeueFile(failedFile);
      await fixture.whenStable();

      expect(mockDialog.open).toHaveBeenCalledTimes(1);
      expect(uploadBoxService.requeueFileUpload).toHaveBeenCalledWith(
        lockedBox.id,
        failedFile,
      );
      expect(mockNotificationService.showSuccess).toHaveBeenCalledWith(
        'The file "failed.fastq.gz" has been queued for re-encryption.',
      );
    });

    it('should escape the file name in the requeue confirmation', async () => {
      mockDialog.open.mockReturnValue({ afterClosed: () => of(false) });

      component.requeueFile({ ...failedFile, alias: 'a&b.bam' });
      await fixture.whenStable();

      const { message } = mockDialog.open.mock.calls[0][1].data;
      expect(message).toContain('<strong>a&amp;b.bam</strong>');
    });

    it('should not requeue a file when the confirmation is cancelled', async () => {
      mockDialog.open.mockReturnValue({ afterClosed: () => of(false) });

      component.requeueFile(failedFile);
      await fixture.whenStable();

      expect(uploadBoxService.requeueFileUpload).not.toHaveBeenCalled();
    });

    it('should warn and refresh when the file is no longer waiting for a retry', async () => {
      const conflict = Object.assign(new Error('Conflict'), {
        status: 409,
        error: { exception_id: 'fileUploadStateError' },
      });
      uploadBoxService.requeueFileUpload.mockReturnValueOnce(
        throwError(() => conflict),
      );

      component.requeueFile(failedFile);
      await fixture.whenStable();

      expect(mockNotificationService.showWarning).toHaveBeenCalledWith(
        'The file "failed.fastq.gz" is no longer waiting for a retry.',
      );
      expect(uploadBoxService.reloadUploadBox).toHaveBeenCalledWith(lockedBox.id);
    });

    it('should ask for a new upload when the uploaded data is gone', async () => {
      const serverError = Object.assign(new Error('Server Error'), {
        status: 500,
        error: { exception_id: 'requeueError' },
      });
      uploadBoxService.requeueFileUpload.mockReturnValueOnce(
        throwError(() => serverError),
      );

      component.requeueFile(failedFile);
      await fixture.whenStable();

      expect(mockNotificationService.showError).toHaveBeenCalledWith(
        'The uploaded data of "failed.fastq.gz" is gone. Delete the file and upload it again.',
      );
      expect(uploadBoxService.reloadUploadBox).not.toHaveBeenCalled();
    });

    it('should report the queued files when all failed files are requeued', async () => {
      uploadBoxService.requeueAllFileUploads.mockReturnValueOnce(
        of({ requeued: ['failed-file'], skipped: [] }),
      );

      screen.getByRole('button', { name: /retry failed re-encryptions/i }).click();
      await fixture.whenStable();

      expect(mockDialog.open).toHaveBeenCalledTimes(1);
      expect(uploadBoxService.requeueAllFileUploads).toHaveBeenCalledWith(lockedBox.id);
      expect(mockNotificationService.showSuccess).toHaveBeenCalledWith(
        '1 file queued for re-encryption.',
      );
      expect(component.isRequeueing()).toBe(false);
    });

    it('should warn when some failed files could not be requeued', async () => {
      uploadBoxService.requeueAllFileUploads.mockReturnValueOnce(
        of({ requeued: ['a', 'b'], skipped: ['c'] }),
      );

      component.requeueAllFiles();
      await fixture.whenStable();

      expect(mockNotificationService.showWarning).toHaveBeenCalledWith(
        '2 files queued for re-encryption. 1 file could not be requeued.',
      );
    });

    it('should tell when no file was waiting for a retry', async () => {
      uploadBoxService.requeueAllFileUploads.mockReturnValueOnce(
        of({ requeued: [], skipped: [] }),
      );

      component.requeueAllFiles();
      await fixture.whenStable();

      expect(mockNotificationService.showInfo).toHaveBeenCalledWith(
        'No files are waiting for a retry of their re-encryption.',
      );
    });

    it('should show an error when requeueing all failed files fails', async () => {
      uploadBoxService.requeueAllFileUploads.mockReturnValueOnce(
        throwError(() => new Error('failed')),
      );

      component.requeueAllFiles();
      await fixture.whenStable();

      expect(mockNotificationService.showError).toHaveBeenCalledWith(
        'The failed files could not be requeued. Please try again.',
      );
      expect(component.isRequeueing()).toBe(false);
      expect(uploadBoxService.reloadUploadBox).not.toHaveBeenCalled();
    });

    it('should refresh when the box was archived before all failed files were requeued', async () => {
      const conflict = Object.assign(new Error('Conflict'), {
        status: 409,
        error: { exception_id: 'boxStateError' },
      });
      uploadBoxService.requeueAllFileUploads.mockReturnValueOnce(
        throwError(() => conflict),
      );

      component.requeueAllFiles();
      await fixture.whenStable();

      expect(mockNotificationService.showError).toHaveBeenCalledWith(
        'Files in archived upload boxes cannot be requeued.',
      );
      expect(uploadBoxService.reloadUploadBox).toHaveBeenCalledWith(lockedBox.id);
    });

    it('should load the complete file list to find files to retry', () => {
      expect(uploadBoxService.loadAllFileUploadsForBox).toHaveBeenCalledWith(
        lockedBox.id,
      );
    });

    it('should hide the whole-box retry when no file failed re-encryption', async () => {
      uploadBoxService.setFileUploads([uploadBox1FileUploads[0]]);
      await fixture.whenStable();

      expect(
        screen.queryByRole('button', { name: /retry failed re-encryptions/i }),
      ).not.toBeInTheDocument();

      // Calling it directly must not requeue anything either.
      component.requeueAllFiles();
      await fixture.whenStable();

      expect(mockDialog.open).not.toHaveBeenCalled();
      expect(uploadBoxService.requeueAllFileUploads).not.toHaveBeenCalled();
    });
  });

  describe('changing the box state', () => {
    beforeEach(() => {
      mockDialog.open.mockReset();
      mockNotificationService.showSuccess.mockClear();
      mockNotificationService.showError.mockClear();
      uploadBoxService.lockUploadBox.mockClear();
      uploadBoxService.lockUploadBox.mockReturnValue(of(undefined));
      uploadBoxService.openUploadBox.mockClear();
      uploadBoxService.openUploadBox.mockReturnValue(of(undefined));
    });

    describe('when the box is open', () => {
      beforeEach(async () => {
        uploadBoxService.setUploadBoxes(uploadBoxes.boxes);
        fixture.componentRef.setInput('id', TEST_BOX.id);
        await fixture.whenStable();
      });

      it('should show the lock button but not the reopen button', () => {
        expect(screen.getByRole('button', { name: /lock the box/i })).toBeVisible();
        expect(
          screen.queryByRole('button', { name: /open the box again/i }),
        ).not.toBeInTheDocument();
      });

      it('should lock the box after confirmation', async () => {
        mockDialog.open.mockReturnValue({ afterClosed: () => of(true) });

        component.lockBox();
        await fixture.whenStable();

        expect(mockDialog.open).toHaveBeenCalledTimes(1);
        expect(uploadBoxService.lockUploadBox).toHaveBeenCalledWith(
          TEST_BOX.id,
          TEST_BOX.version,
          false,
        );
        expect(mockNotificationService.showSuccess).toHaveBeenCalled();
      });

      it('should not lock the box when the confirmation is cancelled', async () => {
        mockDialog.open.mockReturnValue({ afterClosed: () => of(false) });

        component.lockBox();
        await fixture.whenStable();

        expect(uploadBoxService.lockUploadBox).not.toHaveBeenCalled();
        expect(mockNotificationService.showSuccess).not.toHaveBeenCalled();
      });

      it('should offer to force the lock when uploads are incomplete', async () => {
        mockDialog.open.mockReturnValue({ afterClosed: () => of(true) });
        const conflict = Object.assign(new Error('Conflict'), {
          status: 409,
          error: { data: { incomplete_uploads: ['file1', 'file2'] } },
        });
        uploadBoxService.lockUploadBox.mockReturnValueOnce(throwError(() => conflict));

        component.lockBox();
        await fixture.whenStable();

        expect(mockDialog.open).toHaveBeenCalledTimes(2);
        expect(uploadBoxService.lockUploadBox).toHaveBeenLastCalledWith(
          TEST_BOX.id,
          TEST_BOX.version,
          true,
        );
        expect(mockNotificationService.showSuccess).toHaveBeenCalled();
        expect(mockNotificationService.showError).not.toHaveBeenCalled();
      });

      it('should name failed re-encryptions when they block the lock', async () => {
        mockDialog.open.mockReturnValue({ afterClosed: () => of(true) });
        const conflict = Object.assign(new Error('Conflict'), {
          status: 409,
          error: {
            exception_id: 'incompleteOrFailed',
            data: { incomplete_uploads: [], need_attention: ['file1'] },
          },
        });
        uploadBoxService.lockUploadBox.mockReturnValueOnce(throwError(() => conflict));

        component.lockBox();
        await fixture.whenStable();

        expect(mockDialog.open).toHaveBeenNthCalledWith(
          2,
          expect.anything(),
          expect.objectContaining({
            data: expect.objectContaining({
              title: 'Unresolved files detected!',
              message:
                'Locking failed because 1 file failed re-encryption. ' +
                'Do you want to lock the box anyway?',
            }),
          }),
        );
        expect(uploadBoxService.lockUploadBox).toHaveBeenLastCalledWith(
          TEST_BOX.id,
          TEST_BOX.version,
          true,
        );
      });

      it('should show an error notification when locking fails', async () => {
        mockDialog.open.mockReturnValue({ afterClosed: () => of(true) });
        uploadBoxService.lockUploadBox.mockReturnValueOnce(
          throwError(() => new Error('failed')),
        );

        component.lockBox();
        await fixture.whenStable();

        expect(mockNotificationService.showError).toHaveBeenCalled();
        expect(mockNotificationService.showSuccess).not.toHaveBeenCalled();
      });
    });

    describe('when the box is locked', () => {
      const lockedBox = uploadBoxes.boxes[1];

      beforeEach(async () => {
        uploadBoxService.setUploadBoxes(uploadBoxes.boxes);
        fixture.componentRef.setInput('id', lockedBox.id);
        await fixture.whenStable();
      });

      it('should show the reopen button but not the lock button', () => {
        expect(
          screen.getByRole('button', { name: /open the box again/i }),
        ).toBeVisible();
        expect(
          screen.queryByRole('button', { name: /lock the box/i }),
        ).not.toBeInTheDocument();
      });

      it('should reopen the box after confirmation', async () => {
        mockDialog.open.mockReturnValue({ afterClosed: () => of(true) });

        component.openBox();
        await fixture.whenStable();

        expect(mockDialog.open).toHaveBeenCalledTimes(1);
        expect(uploadBoxService.openUploadBox).toHaveBeenCalledWith(
          lockedBox.id,
          lockedBox.version,
        );
        expect(mockNotificationService.showSuccess).toHaveBeenCalled();
      });

      it('should not reopen the box when the confirmation is cancelled', async () => {
        mockDialog.open.mockReturnValue({ afterClosed: () => of(false) });

        component.openBox();
        await fixture.whenStable();

        expect(uploadBoxService.openUploadBox).not.toHaveBeenCalled();
        expect(mockNotificationService.showSuccess).not.toHaveBeenCalled();
      });

      it('should show an error notification when reopening fails', async () => {
        mockDialog.open.mockReturnValue({ afterClosed: () => of(true) });
        uploadBoxService.openUploadBox.mockReturnValueOnce(
          throwError(() => new Error('failed')),
        );

        component.openBox();
        await fixture.whenStable();

        expect(mockNotificationService.showError).toHaveBeenCalled();
        expect(mockNotificationService.showSuccess).not.toHaveBeenCalled();
      });
    });
  });

  describe('deleting the box', () => {
    const archivedBox = uploadBoxes.boxes[2];

    beforeEach(() => {
      mockDialog.open.mockReset();
      mockNavigationService.back.mockClear();
      mockNotificationService.showSuccess.mockClear();
      mockNotificationService.showError.mockClear();
      uploadBoxService.deleteUploadBox.mockClear();
      uploadBoxService.deleteUploadBox.mockReturnValue(of(undefined));
    });

    it('should show an enabled delete button for a non-archived box', async () => {
      uploadBoxService.setUploadBoxes(uploadBoxes.boxes);
      fixture.componentRef.setInput('id', TEST_BOX.id);
      await fixture.whenStable();

      const button = screen.getByRole('button', { name: /delete upload box/i });
      expect(button).toBeVisible();
      expect(button).toBeEnabled();
    });

    it('should show a disabled delete button for an archived box', async () => {
      uploadBoxService.setUploadBoxes(uploadBoxes.boxes);
      fixture.componentRef.setInput('id', archivedBox.id);
      await fixture.whenStable();

      const button = screen.getByRole('button', { name: /delete upload box/i });
      expect(button).toBeVisible();
      expect(button).toBeDisabled();
    });

    it('should delete the box after confirmation and navigate back', async () => {
      uploadBoxService.setUploadBoxes(uploadBoxes.boxes);
      fixture.componentRef.setInput('id', TEST_BOX.id);
      await fixture.whenStable();
      mockDialog.open.mockReturnValue({ afterClosed: () => of(true) });

      component.deleteBox();
      await fixture.whenStable();

      expect(mockDialog.open).toHaveBeenCalledTimes(1);
      expect(uploadBoxService.deleteUploadBox).toHaveBeenCalledWith(
        TEST_BOX.id,
        TEST_BOX.version,
      );
      expect(mockNotificationService.showSuccess).toHaveBeenCalled();
      // goBack() defers the actual navigation with setTimeout; flush it.
      await new Promise((resolve) => setTimeout(resolve));
      expect(mockNavigationService.back).toHaveBeenCalled();
    });

    it('should not delete the box when the confirmation is cancelled', async () => {
      uploadBoxService.setUploadBoxes(uploadBoxes.boxes);
      fixture.componentRef.setInput('id', TEST_BOX.id);
      await fixture.whenStable();
      mockDialog.open.mockReturnValue({ afterClosed: () => of(false) });

      component.deleteBox();
      await fixture.whenStable();

      expect(uploadBoxService.deleteUploadBox).not.toHaveBeenCalled();
      expect(mockNotificationService.showSuccess).not.toHaveBeenCalled();
    });

    it('should not delete an archived box even if called directly', async () => {
      uploadBoxService.setUploadBoxes(uploadBoxes.boxes);
      fixture.componentRef.setInput('id', archivedBox.id);
      await fixture.whenStable();
      mockDialog.open.mockReturnValue({ afterClosed: () => of(true) });

      component.deleteBox();
      await fixture.whenStable();

      expect(mockDialog.open).not.toHaveBeenCalled();
      expect(uploadBoxService.deleteUploadBox).not.toHaveBeenCalled();
    });

    it('should show an error notification when deletion fails', async () => {
      uploadBoxService.setUploadBoxes(uploadBoxes.boxes);
      fixture.componentRef.setInput('id', TEST_BOX.id);
      await fixture.whenStable();
      mockDialog.open.mockReturnValue({ afterClosed: () => of(true) });
      uploadBoxService.deleteUploadBox.mockReturnValueOnce(
        throwError(() => new Error('failed')),
      );

      component.deleteBox();
      await fixture.whenStable();

      expect(mockNotificationService.showError).toHaveBeenCalled();
      expect(mockNotificationService.showSuccess).not.toHaveBeenCalled();
      expect(mockNavigationService.back).not.toHaveBeenCalled();
    });
  });
});
