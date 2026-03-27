/**
 * Test the Upload Box Manager component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialog } from '@angular/material/dialog';
import { NotificationService } from '@app/shared/services/notification';
import { ResearchDataUploadBox, UploadBoxState } from '@app/upload/models/box';
import { UploadBoxService } from '@app/upload/services/upload-box';
import { screen } from '@testing-library/angular';
import { of } from 'rxjs';
import { UploadBoxManagerComponent } from './upload-box-manager';

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
  uploadBoxLocations = () => [];
  uploadBoxLocationOptions = () => [];
  filteredUploadBoxes = () => this.#uploadBoxes();
  storageLabels = {
    value: () => ({}),
    isLoading: () => false,
    error: () => undefined,
  };
  getStorageLocationLabel = (storageAlias: string) => storageAlias;
  loadAllUploadBoxes = vitest.fn();
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

describe('UploadBoxManagerComponent', () => {
  let component: UploadBoxManagerComponent;
  let fixture: ComponentFixture<UploadBoxManagerComponent>;
  let uploadBoxService: MockUploadBoxService;

  beforeEach(async () => {
    mockDialog.open.mockReset();
    mockNotificationService.showSuccess.mockReset();

    await TestBed.configureTestingModule({
      imports: [UploadBoxManagerComponent],
      providers: [
        { provide: UploadBoxService, useClass: MockUploadBoxService },
        { provide: MatDialog, useValue: mockDialog },
        { provide: NotificationService, useValue: mockNotificationService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(UploadBoxManagerComponent);
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

  it('should load all upload boxes upon initialization', () => {
    expect(uploadBoxService.loadAllUploadBoxes).toHaveBeenCalled();
  });

  it('should hide filters when no upload boxes are loaded', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('button.button-primary')).toBeNull();
  });

  it('should show filters when upload boxes are loaded', async () => {
    uploadBoxService.setUploadBoxes([TEST_UPLOAD_BOX]);
    fixture.detectChanges();
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

    expect(uploadBoxService.loadAllUploadBoxes).toHaveBeenCalledTimes(1);
    expect(mockNotificationService.showSuccess).toHaveBeenCalledWith(
      'Upload Box created successfully.',
    );
  });
});
