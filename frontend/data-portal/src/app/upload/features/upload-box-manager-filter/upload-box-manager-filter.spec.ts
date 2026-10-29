/**
 * Test the Upload Box Manager Filter component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import {
  FileStateCountsByBox,
  ResearchDataUploadBox,
  UploadBoxState,
} from '@app/upload/models/box';
import { UploadBoxService } from '@app/upload/services/upload-box';
import { screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';
import { UploadBoxManagerFilter } from './upload-box-manager-filter';

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
  max_size: 10_000_000_000_000,
};

const uploadBoxesSignal = signal<ResearchDataUploadBox[]>([TEST_UPLOAD_BOX]);
const fileStateCountsSignal = signal<FileStateCountsByBox | undefined>({
  [TEST_UPLOAD_BOX.id]: { interrogated: 3 },
});

/**
 * Mock the upload box service as needed by the upload box manager filter component.
 */
const mockUploadBoxService = {
  uploadBoxes: uploadBoxesSignal.asReadonly(),
  fileStateCountsByBox: fileStateCountsSignal.asReadonly(),
  fileStateCounts: {
    error: signal<Error | undefined>(undefined),
    isLoading: signal(false),
  },
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

  /**
   * Set the file state counts for tests.
   * @param counts - the counts to expose, undefined while not loaded
   */
  setFileStateCounts(counts: FileStateCountsByBox | undefined): void {
    fileStateCountsSignal.set(counts);
  },
};

describe('UploadBoxManagerFilter', () => {
  let component: UploadBoxManagerFilter;
  let fixture: ComponentFixture<UploadBoxManagerFilter>;
  let uploadBoxService: typeof mockUploadBoxService;

  beforeEach(async () => {
    mockUploadBoxService.setUploadBoxes([TEST_UPLOAD_BOX]);
    mockUploadBoxService.setFileStateCounts({
      [TEST_UPLOAD_BOX.id]: { interrogated: 3 },
    });
    mockUploadBoxService.fileStateCounts.error.set(undefined);
    mockUploadBoxService.fileStateCounts.isLoading.set(false);
    mockUploadBoxService.setUploadBoxesFilter.mockClear();
    await TestBed.configureTestingModule({
      imports: [UploadBoxManagerFilter],
      providers: [{ provide: UploadBoxService, useValue: mockUploadBoxService }],
    }).compileComponents();

    fixture = TestBed.createComponent(UploadBoxManagerFilter);
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
    const combobox = screen.getByRole('combobox', { name: 'Location' });

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

  it('should set the filter after selecting a group of file states', async () => {
    const combobox = screen.getByRole('combobox', { name: 'File states' });

    await userEvent.click(combobox);
    await fixture.whenStable();

    const option = screen.getByRole('option', { name: 'Some files failed' });
    await userEvent.click(option);
    await fixture.whenStable();

    expect(uploadBoxService.setUploadBoxesFilter).toHaveBeenCalledWith({
      title: undefined,
      state: 'not_archived',
      location: undefined,
      fileStates: 'some_failed',
    });
  });

  it('should offer all conditions before the file state counts are loaded', async () => {
    uploadBoxService.setFileStateCounts(undefined);
    await fixture.whenStable();

    await userEvent.click(screen.getByRole('combobox', { name: 'File states' }));
    await fixture.whenStable();

    for (const name of ['No files yet', 'Some files failed', 'All files ready']) {
      expect(screen.getByRole('option', { name })).toHaveAttribute(
        'aria-disabled',
        'false',
      );
    }
  });

  it('should say why a chosen condition on the file states finds no boxes yet', async () => {
    uploadBoxService.setFileStateCounts(undefined);
    uploadBoxService.fileStateCounts.isLoading.set(true);
    await fixture.whenStable();
    expect(screen.queryByText('Loading the file states…')).toBeNull();

    await userEvent.click(screen.getByRole('combobox', { name: 'File states' }));
    await userEvent.click(screen.getByRole('option', { name: 'Some files failed' }));
    await fixture.whenStable();
    expect(screen.getByText('Loading the file states…')).toBeVisible();

    uploadBoxService.fileStateCounts.isLoading.set(false);
    uploadBoxService.fileStateCounts.error.set(new Error('UCS unavailable'));
    await fixture.whenStable();
    expect(screen.getByText('The file states could not be loaded.')).toBeVisible();

    // An empty box is found without the counts
    await userEvent.click(screen.getByRole('combobox', { name: 'File states' }));
    await userEvent.click(screen.getByRole('option', { name: 'No files yet' }));
    await fixture.whenStable();
    expect(screen.queryByText('The file states could not be loaded.')).toBeNull();
  });

  it('should clear the filter with the remove buttons', async () => {
    const textbox = screen.getByRole('textbox', { name: 'Upload box title' });
    await userEvent.type(textbox, 'Upload Box');
    await userEvent.click(
      screen.getByRole('button', { name: 'Remove filter for upload box title' }),
    );
    await userEvent.click(
      screen.getByRole('button', { name: 'Remove filter for upload box state' }),
    );
    await fixture.whenStable();

    const filter = uploadBoxService.setUploadBoxesFilter.mock.lastCall![0];
    expect(filter.title).toBeFalsy();
    expect(filter.state).toBeUndefined();
    expect(filter.location).toBeUndefined();
    expect(textbox).toHaveValue('');
    expect(screen.getByRole('combobox', { name: 'State' })).toHaveTextContent(
      'All states',
    );
  });

  it('should show "All locations" under its label while no value is chosen', () => {
    expect(screen.getByRole('combobox', { name: 'Location' })).toHaveTextContent(
      'All locations',
    );
  });
});
