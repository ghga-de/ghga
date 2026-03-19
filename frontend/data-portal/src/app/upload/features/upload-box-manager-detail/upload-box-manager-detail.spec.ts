/**
 * Tests for the upload box manager detail component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';
import { uploadBoxes, uploadGrants } from '@app/../mocks/data';
import { fakeActivatedRoute } from '@app/../mocks/route';
import { UserService } from '@app/auth/services/user';
import { NavigationTrackingService } from '@app/shared/services/navigation';
import { NotificationService } from '@app/shared/services/notification';
import { ResearchDataUploadBox } from '@app/upload/models/box';
import { UploadGrant } from '@app/upload/models/grant';
import { UploadBoxService } from '@app/upload/services/upload-box';
import { screen } from '@testing-library/angular';
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
  #fileUploadsList = signal<never[]>([]);

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
}

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
        { provide: UploadBoxService, useClass: MockUploadBoxService },
        { provide: UserService, useClass: MockUserService },
        { provide: NavigationTrackingService, useValue: mockNavigationService },
        { provide: NotificationService, useValue: mockNotificationService },
        { provide: ActivatedRoute, useValue: fakeActivatedRoute },
      ],
    }).compileComponents();

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

    it('should not call loadUploadBox when box is found in list', () => {
      expect(uploadBoxService.loadUploadBox).not.toHaveBeenCalled();
    });

    it('should call loadBoxGrants with the box id', () => {
      expect(uploadBoxService.loadBoxGrants).toHaveBeenCalledWith(TEST_BOX.id);
    });

    it('should display upload grants when available', async () => {
      uploadBoxService.setBoxGrants(uploadGrants);
      await fixture.whenStable();
      expect(screen.getByText('John Doe (doe@home.org)')).toBeVisible();
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
});
