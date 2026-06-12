/**
 * Tests for the upload box manager detail component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialog } from '@angular/material/dialog';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { uploadBox1FileUploads, uploadBoxes, uploadGrants } from '@app/../mocks/data';
import { fakeActivatedRoute } from '@app/../mocks/route';
import { UserService } from '@app/auth/services/user';
import { MetadataService } from '@app/metadata/services/metadata';
import { MetadataSearchService } from '@app/metadata/services/metadata-search';
import { NavigationTrackingService } from '@app/shared/services/navigation';
import { NotificationService } from '@app/shared/services/notification';
import { ResearchDataUploadBox, UploadBoxState } from '@app/upload/models/box';
import { FileUploadWithAccession } from '@app/upload/models/file-upload';
import { UploadGrant } from '@app/upload/models/grant';
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
    value: this.#fileUploadsList.asReadonly(),
    isLoading: () => false,
    error: () => undefined,
  };

  storageLabels = {
    value: () => ({ TUE01: 'Tübingen 1' }) as Record<string, string>,
    error: () => undefined,
  };

  loadUploadBox = vitest.fn();
  loadStorageLabels = vitest.fn();
  loadBoxGrants = vitest.fn();
  loadFileUploadsForBox = vitest.fn();
  addUploadGrant = vitest.fn();
  submitFileMapping = vitest.fn(() => of(undefined));
  archiveUploadBox = vitest.fn(() => of(undefined));
  deleteFileUpload = vitest.fn(() => of(undefined));
  lockUploadBox = vitest.fn(() => of(undefined));
  openUploadBox = vitest.fn(() => of(undefined));

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
 * Minimal mock of MetadataSearchService for the embedded mapping component.
 */
class MockMetadataSearchService {
  loadStudiesMap = vitest.fn(() => of(new Map()));
}

/**
 * Minimal mock of MetadataService for the embedded mapping component.
 */
class MockMetadataService {
  filesOfStudy = vitest.fn(() => of([]));
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
const mockNotificationService = { showError: vitest.fn(), showSuccess: vitest.fn() };

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
        { provide: MetadataSearchService, useClass: MockMetadataSearchService },
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

    it('should call loadUploadBox to keep detail state synchronized', () => {
      expect(uploadBoxService.loadUploadBox).toHaveBeenCalledWith(TEST_BOX.id);
    });

    it('should call loadBoxGrants with the box id', () => {
      expect(uploadBoxService.loadBoxGrants).toHaveBeenCalledWith(TEST_BOX.id);
    });

    it('should display upload grants when available', async () => {
      uploadBoxService.setBoxGrants(uploadGrants);
      await fixture.whenStable();
      expect(screen.getAllByText('John Doe (doe@home.org)')).toHaveLength(3);
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

    it('should call loadUploadBox with the correct id', () => {
      expect(uploadBoxService.loadUploadBox).toHaveBeenCalledWith(TEST_BOX.id);
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
});
