/**
 * Test the Upload Box Manager component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialog } from '@angular/material/dialog';
import { routes } from '@app/app-routes';
import { UserService } from '@app/auth/services/user';
import { pendingEditsGuard } from '@app/shared/features/pending-edits';
import { Notifier } from '@app/shared/services/notification';
import { ResearchDataUploadBox, UploadBoxState } from '@app/upload/models/box';
import { UploadBoxPriority } from '@app/upload/models/box-priority';
import { UploadBoxService } from '@app/upload/services/upload-box';
import { screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';
import { of } from 'rxjs';
import { UploadBoxManager } from './upload-box-manager';

const TEST_UPLOAD_BOX: ResearchDataUploadBox = {
  id: '0a36607a-b53f-49ed-bf3e-a5f2dbc68009',
  version: 1,
  state: UploadBoxState.open,
  title: 'Upload Box Test',
  description: 'Upload box used in manager component tests',
  last_changed: '2025-02-01T09:00:00Z',
  changed_by: 'doe@test.dev',
  file_count: 3,
  size: 123456,
  storage_alias: 'TUE01',
  max_size: 10_000_000_000_000,
};

const OTHER_UPLOAD_BOX: ResearchDataUploadBox = {
  ...TEST_UPLOAD_BOX,
  id: '0a36607a-b53f-49ed-bf3e-a5f2dbc68010',
  title: 'Other Upload Box',
};

const TEST_PRIORITY: UploadBoxPriority = {
  version: 3,
  entries: [],
  changed_by: null,
  last_changed: '2025-02-10T14:30:00Z',
};

/**
 * Mock the upload box service as needed by the upload box manager component.
 */
class MockUploadBoxService {
  #uploadBoxes = signal<ResearchDataUploadBox[]>([]);

  boxRetrievalResults = {
    value: () => ({ count: this.#uploadBoxes().length, boxes: this.#uploadBoxes() }),
    isLoading: () => false,
    error: () => undefined,
  };
  uploadBoxes = this.#uploadBoxes.asReadonly();
  uploadBoxesFilter = () => ({
    title: undefined,
    state: undefined,
    location: undefined,
  });
  uploadBoxLocationOptions = () => [];
  filteredUploadBoxes = () => this.#uploadBoxes();
  fileStateCounts = { isLoading: () => false, error: () => undefined };
  fileStateCountsByBox = () => ({});
  showFileStateCountsOf = vitest.fn();
  boxPriority = {
    value: () => TEST_PRIORITY,
    error: () => undefined,
    isLoading: () => false,
  };
  prioritizedUploadBoxes = signal<ResearchDataUploadBox[] | undefined>(undefined);
  storageLabels = {
    value: () => ({}),
    isLoading: () => false,
    error: () => undefined,
  };
  getStorageLocationLabel = (storageAlias: string) => storageAlias;
  loadAllUploadBoxes = vitest.fn();
  reloadAllUploadBoxes = vitest.fn();
  setUploadBoxesFilter = vitest.fn();

  /**
   * Set upload boxes for tests.
   * @param uploadBoxes - upload boxes to expose
   */
  setUploadBoxes(uploadBoxes: ResearchDataUploadBox[]) {
    this.#uploadBoxes.set(uploadBoxes);
  }
}

const mockDialog = {
  open: vitest.fn(),
};

const mockNotificationService = {
  showSuccess: vitest.fn(),
};

const mockUserService = {
  createUserFetcher: () => ({
    load: vitest.fn(),
    resource: { value: () => undefined, error: () => undefined },
  }),
};

describe('UploadBoxManager', () => {
  let component: UploadBoxManager;
  let fixture: ComponentFixture<UploadBoxManager>;
  let uploadBoxService: MockUploadBoxService;

  beforeEach(async () => {
    mockDialog.open.mockReset();
    mockNotificationService.showSuccess.mockReset();

    await TestBed.configureTestingModule({
      imports: [UploadBoxManager],
      providers: [
        { provide: UploadBoxService, useClass: MockUploadBoxService },
        { provide: MatDialog, useValue: mockDialog },
        { provide: Notifier, useValue: mockNotificationService },
        { provide: UserService, useValue: mockUserService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(UploadBoxManager);
    uploadBoxService = TestBed.inject(
      UploadBoxService,
    ) as unknown as MockUploadBoxService;
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should show the proper heading', () => {
    const heading = screen.getByRole('heading', { level: 1 });
    expect(heading).toHaveTextContent('Upload Box Manager');
  });

  it('should fetch all upload boxes again upon initialization', () => {
    expect(uploadBoxService.reloadAllUploadBoxes).toHaveBeenCalled();
  });

  it('should fetch all upload boxes again when the refresh button is used', () => {
    screen.getByRole('button', { name: 'Refresh the upload boxes' }).click();
    expect(uploadBoxService.reloadAllUploadBoxes).toHaveBeenCalledTimes(2);
  });

  it('should hide filters when no upload boxes are loaded', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('button.button-primary')).toBeNull();
  });

  it('should show filters when upload boxes are loaded', async () => {
    uploadBoxService.setUploadBoxes([TEST_UPLOAD_BOX]);
    await fixture.whenStable();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('button.button-primary')).toBeTruthy();
  });

  it('should display the create Upload Box button', () => {
    expect(screen.getByRole('button', { name: /create upload box/i })).toBeVisible();
  });

  it('should open the create Upload Box dialog when clicking the button', () => {
    mockDialog.open.mockReturnValue({ afterClosed: () => of(undefined) });

    screen.getByRole('button', { name: /create upload box/i }).click();

    expect(mockDialog.open).toHaveBeenCalled();
  });

  it('should notify on successful dialog result', () => {
    mockDialog.open.mockReturnValue({ afterClosed: () => of('new-box-id') });

    component.openCreateUploadBoxDialog();

    expect(uploadBoxService.reloadAllUploadBoxes).toHaveBeenCalledTimes(1);
    expect(mockNotificationService.showSuccess).toHaveBeenCalledWith(
      'Upload Box created successfully.',
    );
  });

  describe('reorder mode', () => {
    beforeEach(async () => {
      uploadBoxService.setUploadBoxes([TEST_UPLOAD_BOX, OTHER_UPLOAD_BOX]);
      uploadBoxService.prioritizedUploadBoxes.set([TEST_UPLOAD_BOX, OTHER_UPLOAD_BOX]);
      await fixture.whenStable();
    });

    /**
     * Click a button and wait for the page to update.
     * @param name - the accessible name of the button
     */
    async function click(name: string): Promise<void> {
      await userEvent.click(screen.getByRole('button', { name }));
      await fixture.whenStable();
    }

    it('should disable Change order if the priority order is not loaded', async () => {
      const changePriority = screen.getByRole('button', { name: 'Change order' });
      expect(changePriority).toBeEnabled();

      uploadBoxService.prioritizedUploadBoxes.set(undefined);
      await fixture.whenStable();
      expect(changePriority).toBeDisabled();
    });

    it('should switch between the list and the reorder mode', async () => {
      await click('Change order');

      expect(screen.getByRole('heading', { name: 'Priority order' })).toBeVisible();
      expect(screen.getByRole('list', { name: 'Priority order' })).toBeVisible();
      expect(screen.queryByRole('button', { name: /create upload box/i })).toBeNull();
      expect(screen.queryByRole('button', { name: 'Change order' })).toBeNull();

      await click('Cancel');

      expect(screen.queryByRole('heading', { name: 'Priority order' })).toBeNull();
      expect(screen.getByRole('button', { name: /create upload box/i })).toBeVisible();
    });

    it('should report unsaved changes to the leave guard until Cancel', async () => {
      expect(component.hasPendingEdits()).toBe(false);

      await click('Change order');
      expect(component.hasPendingEdits()).toBe(false);

      await click('Move Other Upload Box up');
      expect(component.hasPendingEdits()).toBe(true);

      await click('Cancel');
      expect(component.hasPendingEdits()).toBe(false);
    });

    it('should guard the page against leaving with unsaved changes', () => {
      const manager = routes.find((route) => route.path === 'upload-box-manager');
      const list = manager?.children?.find((route) => route.path === '');
      expect(list?.canDeactivate).toContain(pendingEditsGuard);
    });
  });
});
