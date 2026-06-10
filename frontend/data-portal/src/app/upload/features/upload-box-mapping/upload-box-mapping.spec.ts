/**
 * Tests for the upload box mapping component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialog } from '@angular/material/dialog';
import { provideRouter } from '@angular/router';
import { uploadBoxes } from '@app/../mocks/data';
import { EmFile } from '@app/metadata/models/dataset-information';
import { Study } from '@app/metadata/models/study';
import { MetadataService } from '@app/metadata/services/metadata';
import { MetadataSearchService } from '@app/metadata/services/metadata-search';
import { NavigationTrackingService } from '@app/shared/services/navigation';
import { NotificationService } from '@app/shared/services/notification';
import { UploadBoxState } from '@app/upload/models/box';
import { FileUploadWithAccession } from '@app/upload/models/file-upload';
import { UploadBoxService } from '@app/upload/services/upload-box';
import {
  MappingSnapshot,
  UploadBoxMappingStateService,
} from '@app/upload/services/upload-box-mapping-state';
import { of, throwError } from 'rxjs';
import { UploadBoxMappingComponent } from './upload-box-mapping';
import { UploadBoxMappingConfirmDialogComponent } from './upload-box-mapping-confirm-dialog';

const TEST_BOX = {
  ...uploadBoxes.boxes[0],
  id: 'box-1',
  version: 4,
  state: UploadBoxState.locked,
  file_count: 3,
};

const TEST_STUDY: Study = {
  accession: 'STUDY-001',
  alias: 'study-alias',
  title: 'Study Title',
  description: 'Study Description',
  types: [],
  ega_accession: 'EGAS000001',
  affiliations: [],
  datasets: ['DS1'],
  publications: [],
};

const TEST_METADATA_FILES: EmFile[] = [
  {
    accession: 'meta-1',
    alias: 'Case.fastq.gz',
    name: 'Sample-1.fastq.gz',
    format: 'fastq.gz',
  },
  {
    accession: 'meta-2',
    alias: 'other.fastq.gz',
    name: 'Sample-2.fastq.gz',
    format: 'fastq.gz',
  },
  {
    accession: 'meta-3',
    alias: 'dup.fastq.gz',
    name: 'Sample-3.fastq.gz',
    format: 'fastq.gz',
  },
];

const TEST_BOX_FILES: FileUploadWithAccession[] = [
  {
    id: 'file-1',
    box_id: 'box-1',
    alias: 'Case.fastq.gz',
    state: 'interrogated',
    state_updated: '2025-01-01T00:00:00Z',
    storage_alias: 'TUE01',
    bucket_id: 'bucket-1',
    decrypted_sha256: null,
    decrypted_size: 1024,
    encrypted_size: 1536,
    part_size: 512,
    accession: null,
  },
  {
    id: 'file-2',
    box_id: 'box-1',
    alias: 'OTHER.fastq.gz',
    state: 'interrogated',
    state_updated: '2025-01-01T00:00:00Z',
    storage_alias: 'TUE01',
    bucket_id: 'bucket-2',
    decrypted_sha256: null,
    decrypted_size: 2048,
    encrypted_size: 2560,
    part_size: 512,
    accession: null,
  },
  {
    id: 'file-3',
    box_id: 'box-1',
    alias: 'DUP.fastq.gz',
    state: 'interrogated',
    state_updated: '2025-01-01T00:00:00Z',
    storage_alias: 'TUE01',
    bucket_id: 'bucket-3',
    decrypted_sha256: null,
    decrypted_size: 4096,
    encrypted_size: 4608,
    part_size: 512,
    accession: null,
  },
];

/**
 * Minimal mock of UploadBoxService for mapping component tests.
 */
class MockUploadBoxService {
  #boxFileUploads = signal<FileUploadWithAccession[]>([]);

  boxFileUploads = {
    value: this.#boxFileUploads.asReadonly(),
    isLoading: () => false,
    error: () => undefined,
  };

  submitFileMapping = vitest.fn();
  archiveUploadBox = vitest.fn();

  /**
   * Set the box file uploads exposed to the component.
   * @param files - file uploads for the current box
   */
  setBoxFileUploads(files: FileUploadWithAccession[]): void {
    this.#boxFileUploads.set(files);
  }
}

/**
 * Minimal mock of MetadataSearchService for mapping component tests.
 */
class MockMetadataSearchService {
  studiesMap = new Map<string, Study>([[TEST_STUDY.accession, TEST_STUDY]]);

  loadStudiesMap = vitest.fn(() => of(this.studiesMap));
}

/**
 * Minimal mock of MetadataService for mapping component tests.
 */
class MockMetadataService {
  files = TEST_METADATA_FILES;

  filesOfStudy = vitest.fn(() => of(this.files));
}

const mockNotificationService = {
  showError: vitest.fn(),
  showInfo: vitest.fn(),
  showSuccess: vitest.fn(),
};
const mockNavigationService = { back: vitest.fn() };
const mockDialog = { open: vitest.fn() };
const mockMappingStateService = {
  snapshotFor: vitest.fn<(boxId: string) => MappingSnapshot | undefined>(),
  saveSnapshot: vitest.fn(),
  clearSnapshot: vitest.fn(),
};

describe('UploadBoxMappingComponent', () => {
  let component: UploadBoxMappingComponent;
  let fixture: ComponentFixture<UploadBoxMappingComponent>;
  let uploadBoxService: MockUploadBoxService;

  /**
   * Create the component with an optional saved snapshot.
   * @param snapshot - optional mapping state restored during ngOnInit
   * @returns the created fixture
   */
  async function createComponent(snapshot?: MappingSnapshot): Promise<void> {
    mockMappingStateService.snapshotFor.mockReturnValue(snapshot);
    fixture = TestBed.createComponent(UploadBoxMappingComponent);
    fixture.componentRef.setInput('box', TEST_BOX);
    component = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  }

  beforeEach(async () => {
    mockDialog.open.mockReset();
    mockNotificationService.showError.mockReset();
    mockNotificationService.showInfo.mockReset();
    mockNotificationService.showSuccess.mockReset();
    mockNavigationService.back.mockReset();
    mockMappingStateService.snapshotFor.mockReset();
    mockMappingStateService.saveSnapshot.mockReset();
    mockMappingStateService.clearSnapshot.mockReset();
    mockMappingStateService.snapshotFor.mockReturnValue(undefined);

    await TestBed.configureTestingModule({
      imports: [UploadBoxMappingComponent],
      providers: [
        provideRouter([]),
        { provide: UploadBoxService, useClass: MockUploadBoxService },
        { provide: MetadataSearchService, useClass: MockMetadataSearchService },
        { provide: MatDialog, useValue: mockDialog },
        { provide: NotificationService, useValue: mockNotificationService },
        { provide: NavigationTrackingService, useValue: mockNavigationService },
        {
          provide: UploadBoxMappingStateService,
          useValue: mockMappingStateService,
        },
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
    uploadBoxService.setBoxFileUploads(TEST_BOX_FILES);

    await createComponent();
  });

  it('should restore a saved snapshot on init', async () => {
    await createComponent({
      studyAccession: TEST_STUDY.accession,
      mappedField: 'name',
      manualMappings: [['meta-3', 'file-3']],
    });

    expect(component.selectedStudyAccession()).toBe(TEST_STUDY.accession);
    expect(component.committedMappedField()).toBe('name');
    expect(component.pendingMappedField()).toBe('name');
    expect(component.manualMappings()).toEqual(new Map([['meta-3', 'file-3']]));
  });

  it('should compute exact and unique case-insensitive auto mappings without reusing a box file', async () => {
    await createComponent({
      studyAccession: TEST_STUDY.accession,
      mappedField: 'alias',
      manualMappings: [],
    });

    expect(component.autoMappings()).toEqual(
      new Map([
        ['meta-1', 'file-1'],
        ['meta-2', 'file-2'],
        ['meta-3', 'file-3'],
      ]),
    );
  });

  it('should confirm field changes before discarding manual mappings', async () => {
    await createComponent({
      studyAccession: TEST_STUDY.accession,
      mappedField: 'alias',
      manualMappings: [['meta-3', 'file-3']],
    });
    mockDialog.open.mockReturnValueOnce({ afterClosed: () => of(false) });

    component.pendingMappedField.set('name');
    fixture.detectChanges();
    await fixture.whenStable();

    expect(mockDialog.open).toHaveBeenCalled();
    expect(component.committedMappedField()).toBe('alias');
    expect(component.pendingMappedField()).toBe('alias');
    expect(component.manualMappings()).toEqual(new Map([['meta-3', 'file-3']]));

    mockDialog.open.mockReturnValueOnce({ afterClosed: () => of(true) });
    component.pendingMappedField.set('name');
    fixture.detectChanges();
    await fixture.whenStable();

    expect(component.committedMappedField()).toBe('name');
    expect(component.manualMappings()).toEqual(new Map());
  });

  it('should allow a manual remap to an unused box file and reject a reused one', async () => {
    await createComponent({
      studyAccession: TEST_STUDY.accession,
      mappedField: 'alias',
      manualMappings: [],
    });

    const unmappedRow = component
      .mappingRows()
      .find((row) => row.metadataFile.accession === 'meta-3');
    expect(unmappedRow).toBeDefined();

    component.startEditing(unmappedRow!);
    component.inlineInputValue.set('OTHER.fastq.gz');
    component.commitInlineEdit(unmappedRow!);

    expect(component.manualMappings()).toEqual(new Map());
    expect(component.editingMetaAccession()).toBeNull();

    component.startEditing(unmappedRow!);
    component.inlineInputValue.set('DUP.fastq.gz');
    component.commitInlineEdit(unmappedRow!);

    expect(component.manualMappings()).toEqual(new Map([['meta-3', 'file-3']]));
  });

  it('should submit the mapping, archive the box, clear saved state, and emit archived on success', async () => {
    await createComponent({
      studyAccession: TEST_STUDY.accession,
      mappedField: 'alias',
      manualMappings: [
        ['meta-1', 'file-1'],
        ['meta-2', 'file-2'],
        ['meta-3', 'file-3'],
      ],
    });
    const archivedSpy = vitest.fn();
    component.archived.subscribe(archivedSpy);
    uploadBoxService.submitFileMapping.mockReturnValue(of(undefined));
    uploadBoxService.archiveUploadBox.mockReturnValue(of(undefined));
    mockDialog.open.mockReturnValue({ afterClosed: () => of(true) });
    mockDialog.open.mockClear();

    component.onConfirmAndArchive();

    expect(mockDialog.open).toHaveBeenCalledWith(
      UploadBoxMappingConfirmDialogComponent,
      expect.objectContaining({
        data: {
          unmappedBoxFileAliases: [],
          unmappedMetaFileNames: [],
        },
      }),
    );
    expect(uploadBoxService.submitFileMapping).toHaveBeenCalledWith('box-1', {
      box_version: 4,
      study_id: TEST_STUDY.accession,
      mapping: {
        'meta-1': 'file-1',
        'meta-2': 'file-2',
        'meta-3': 'file-3',
      },
    });
    expect(uploadBoxService.archiveUploadBox).toHaveBeenCalledWith('box-1', 5);
    expect(mockMappingStateService.clearSnapshot).toHaveBeenCalledWith('box-1');
    expect(mockNotificationService.showSuccess).toHaveBeenCalledWith(
      'File mapping submitted and upload box archived successfully.',
    );
    expect(archivedSpy).toHaveBeenCalled();
  });

  it('should show an error and skip archival when submitting the mapping fails', async () => {
    await createComponent({
      studyAccession: TEST_STUDY.accession,
      mappedField: 'alias',
      manualMappings: [['meta-1', 'file-1']],
    });
    uploadBoxService.submitFileMapping.mockReturnValue(
      throwError(() => new Error('mapping failed')),
    );
    mockDialog.open.mockReturnValue({ afterClosed: () => of(true) });
    mockDialog.open.mockClear();

    component.onConfirmAndArchive();

    expect(uploadBoxService.archiveUploadBox).not.toHaveBeenCalled();
    expect(mockNotificationService.showError).toHaveBeenCalledWith(
      'Failed to submit the file mapping.',
    );
  });

  it('should show a specific error when archival fails after a successful mapping submission', async () => {
    await createComponent({
      studyAccession: TEST_STUDY.accession,
      mappedField: 'alias',
      manualMappings: [['meta-1', 'file-1']],
    });
    uploadBoxService.submitFileMapping.mockReturnValue(of(undefined));
    uploadBoxService.archiveUploadBox.mockReturnValue(
      throwError(() => new Error('archival failed')),
    );
    mockDialog.open.mockReturnValue({ afterClosed: () => of(true) });
    mockDialog.open.mockClear();

    component.onConfirmAndArchive();

    expect(mockNotificationService.showError).toHaveBeenCalledWith(
      'Mapping was submitted but archival failed.',
    );
  });

  it('should reset manual mappings and notify when reset is requested', () => {
    component.manualMappings.set(new Map([['meta-3', 'file-3']]));

    component.onReset();

    expect(component.manualMappings()).toEqual(new Map());
    expect(mockNotificationService.showInfo).toHaveBeenCalledWith(
      'Manual mappings have been reset.',
    );
  });
});
