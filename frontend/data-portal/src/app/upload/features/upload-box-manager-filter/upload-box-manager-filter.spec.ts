/**
 * Test the Upload Box Manager Filter component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ResearchDataUploadBox, UploadBoxState } from '@app/upload/models/box';
import { UploadBoxService } from '@app/upload/services/upload-box';
import { screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';
import { UploadBoxManagerFilterComponent } from './upload-box-manager-filter';

const TEST_UPLOAD_BOX: ResearchDataUploadBox = {
  id: '0a36607a-b53f-49ed-bf3e-a5f2dbc68009',
  version: 1,
  state: UploadBoxState.open,
  title: 'Upload Box Test',
  description: 'Upload box used in filter component tests',
  last_changed: '2025-02-01T09:00:00Z',
  changed_by: 'doe@test.dev',
  file_count: 3,
  size: 123456,
  storage_alias: 'TUE01',
};

const uploadBoxesSignal = signal<ResearchDataUploadBox[]>([TEST_UPLOAD_BOX]);

/**
 * Mock the upload box service as needed by the upload box manager filter component.
 */
const mockUploadBoxService = {
  uploadBoxes: uploadBoxesSignal.asReadonly(),
  uploadBoxesFilter: () => ({
    title: undefined,
    state: undefined,
    location: undefined,
  }),
  uploadBoxLocationOptions: () => [
    { value: 'HD02', label: 'Heidelberg 2' },
    { value: 'TUE01', label: 'Tübingen 1' },
  ],
  setUploadBoxesFilter: vitest.fn(),

  /**
   * Set upload boxes for tests.
   * @param uploadBoxes - upload boxes to expose
   */
  setUploadBoxes(uploadBoxes: ResearchDataUploadBox[]): void {
    uploadBoxesSignal.set(uploadBoxes);
  },
};

describe('UploadBoxManagerFilterComponent', () => {
  let component: UploadBoxManagerFilterComponent;
  let fixture: ComponentFixture<UploadBoxManagerFilterComponent>;
  let uploadBoxService: typeof mockUploadBoxService;

  beforeEach(async () => {
    mockUploadBoxService.setUploadBoxes([TEST_UPLOAD_BOX]);
    mockUploadBoxService.setUploadBoxesFilter.mockClear();
    await TestBed.configureTestingModule({
      imports: [UploadBoxManagerFilterComponent],
      providers: [{ provide: UploadBoxService, useValue: mockUploadBoxService }],
    }).compileComponents();

    fixture = TestBed.createComponent(UploadBoxManagerFilterComponent);
    component = fixture.componentInstance;
    uploadBoxService = TestBed.inject(
      UploadBoxService,
    ) as unknown as typeof mockUploadBoxService;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should reset the filter upon initialization', async () => {
    expect(uploadBoxService.setUploadBoxesFilter).toHaveBeenCalledWith({
      title: undefined,
      state: 'not_archived',
      location: undefined,
    });
  });

  it('should hide filter controls when no upload boxes are loaded', async () => {
    uploadBoxService.setUploadBoxes([]);
    fixture.detectChanges();
    await fixture.whenStable();

    const filterButton = screen.queryByRole('button', {
      name: 'Filter upload boxes',
    });
    expect(filterButton).toBeNull();
  });

  it('should show filter controls when upload boxes are loaded', () => {
    const filterButton = screen.queryByRole('button', {
      name: 'Filter upload boxes',
    });
    expect(filterButton).toBeTruthy();
  });

  it('should set the filter after typing a title', async () => {
    const textbox = screen.getByRole('textbox', { name: 'Upload box title' });

    await userEvent.type(textbox, 'Upload Box');
    await fixture.whenStable();

    expect(uploadBoxService.setUploadBoxesFilter).toHaveBeenCalledWith({
      title: 'Upload Box',
      state: 'not_archived',
      location: undefined,
    });
  });

  it('should set the filter after selecting a state', async () => {
    const combobox = screen.getByRole('combobox', { name: 'State' });

    await userEvent.click(combobox);
    await fixture.whenStable();

    const option = screen.getByRole('option', { name: 'Open' });
    await userEvent.click(option);
    await fixture.whenStable();

    expect(uploadBoxService.setUploadBoxesFilter).toHaveBeenCalledWith({
      title: undefined,
      state: UploadBoxState.open,
      location: undefined,
    });
  });

  it('should set the filter after selecting a location', async () => {
    const combobox = screen.getByRole('combobox', { name: 'All locations' });

    await userEvent.click(combobox);
    await fixture.whenStable();

    const option = screen.getByRole('option', { name: 'Heidelberg 2' });
    await userEvent.click(option);
    await fixture.whenStable();

    expect(uploadBoxService.setUploadBoxesFilter).toHaveBeenCalledWith({
      title: undefined,
      state: 'not_archived',
      location: 'HD02',
    });
  });
});
