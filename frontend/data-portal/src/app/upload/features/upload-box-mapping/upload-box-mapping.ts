/**
 * File mapping card component for the upload box manager detail page.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  input,
  OnInit,
  output,
  signal,
  viewChild,
} from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatRadioModule } from '@angular/material/radio';
import { MatSelectModule } from '@angular/material/select';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { RouterLink } from '@angular/router';
import { catchError, concatMap, of, switchMap, throwError } from 'rxjs';

import { EmFile } from '@app/metadata/models/dataset-information';
import { Study } from '@app/metadata/models/study';
import { MetadataService } from '@app/metadata/services/metadata';
import { MetadataSearchService } from '@app/metadata/services/metadata-search';
import { NavigationTrackingService } from '@app/shared/services/navigation';
import { NotificationService } from '@app/shared/services/notification';
import {
  ConfirmDialogComponent,
  ConfirmDialogData,
} from '@app/shared/ui/confirm-dialog/confirm-dialog';
import { ResearchDataUploadBox } from '@app/upload/models/box';
import { FileUploadWithAccession } from '@app/upload/models/file-upload';
import { MappedField } from '@app/upload/models/mapping';
import { UploadBoxService } from '@app/upload/services/upload-box';
import { UploadBoxMappingStateService } from '@app/upload/services/upload-box-mapping-state';
import {
  MappingConfirmDialogData,
  UploadBoxMappingConfirmDialogComponent,
} from './upload-box-mapping-confirm-dialog';

/** A single row in the mapping table */
export interface MappingRow {
  /** The metadata file entry */
  metadataFile: EmFile;
  /** The matched upload-box file, if any */
  boxFile: FileUploadWithAccession | undefined;
  /** How the mapping was established */
  mappingType: 'exact' | 'manual' | 'none';
}

/**
 * Sort key for a filename: "{extension}:{basename}" for grouping by extension
 * @param filename - the filename to generate a sort key for
 * @returns a string key that groups files by extension then sorts alphabetically
 */
function fileSortKey(filename: string | undefined): string {
  if (!filename) return '\xff'; // sort absent names last
  const lower = filename.toLowerCase();
  const dot = lower.lastIndexOf('.');
  if (dot < 0) return `\xfe:${lower}`; // files without extension sort just above absent
  return `${lower.slice(dot + 1)}:${lower}`;
}

/**
 * Compute automatic mappings between metadata files and upload-box files.
 * Case-sensitive exact match takes priority; falls back to the single
 * case-insensitive match if exactly one exists. Box files are not reused.
 * @param metaFiles - metadata files to match
 * @param boxFiles - upload-box files to match against
 * @param field - which metadata field to compare against the box file alias
 * @returns Map from metadata file accession to matched box file ID
 */
function computeAutoMappings(
  metaFiles: EmFile[],
  boxFiles: FileUploadWithAccession[],
  field: MappedField | undefined,
): Map<string, string> {
  const result = new Map<string, string>();
  if (!field || !metaFiles.length || !boxFiles.length) return result;

  const usedBoxIds = new Set<string>();

  for (const meta of metaFiles) {
    const metaValue = meta[field];
    if (!metaValue) continue;

    // Case-sensitive exact match
    const exact = boxFiles.find(
      (bf) => bf.alias === metaValue && !usedBoxIds.has(bf.id),
    );
    if (exact) {
      result.set(meta.accession, exact.id);
      usedBoxIds.add(exact.id);
      continue;
    }

    // Case-insensitive single match
    const lower = metaValue.toLowerCase();
    const caseMatches = boxFiles.filter(
      (bf) => bf.alias.toLowerCase() === lower && !usedBoxIds.has(bf.id),
    );
    if (caseMatches.length === 1) {
      result.set(meta.accession, caseMatches[0].id);
      usedBoxIds.add(caseMatches[0].id);
    }
  }

  return result;
}

/**
 * Embedded card for establishing a mapping between metadata file accessions
 * and upload box file IDs. Appears automatically when the box state is "locked".
 */
@Component({
  selector: 'app-upload-box-mapping',
  imports: [
    FormsModule,
    MatAutocompleteModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatPaginatorModule,
    MatRadioModule,
    MatSelectModule,
    MatSortModule,
    MatTableModule,
    RouterLink,
  ],
  providers: [MetadataService],
  templateUrl: './upload-box-mapping.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UploadBoxMappingComponent implements OnInit {
  #uploadBoxService = inject(UploadBoxService);
  #metadataSearchService = inject(MetadataSearchService);
  #metadataService = inject(MetadataService);
  #dialog = inject(MatDialog);
  #notificationService = inject(NotificationService);
  #mappingStateService = inject(UploadBoxMappingStateService);
  #navigationService = inject(NavigationTrackingService);

  /** The locked upload box */
  box = input.required<ResearchDataUploadBox>();

  /** Emitted after a successful mapping submission */
  archived = output<void>();

  /** Currently selected study accession */
  selectedStudyAccession = signal<string | undefined>(undefined);

  /** The metadata field currently committed for auto-matching */
  committedMappedField = signal<MappedField | undefined>(undefined);

  /**
   * The metadata field value bound to the dropdown.
   * Changes are staged here and committed (with confirmation) via an effect.
   */
  pendingMappedField = signal<MappedField | undefined>(undefined);

  /** Text used to filter table rows */
  filterText = signal<string>('');

  /**
   * Manual mappings: meta accession → box file ID.
   * A `null` value means the mapping was explicitly cleared.
   */
  manualMappings = signal<Map<string, string | null>>(new Map());

  /** The metadata file accession currently open for inline editing */
  editingMetaAccession = signal<string | null>(null);

  /** The current text value in the inline editor */
  inlineInputValue = signal<string>('');

  /** Whether a mapping submission is in progress */
  isSubmitting = signal<boolean>(false);

  /** Guard to prevent opening a second field-change confirmation dialog */
  #fieldChangeDialogOpen = signal<boolean>(false);

  // Async data

  private readonly studiesMap$ = this.#metadataSearchService.loadStudiesMap();

  /** All available studies, keyed by accession */
  studiesMap = toSignal(this.studiesMap$, { initialValue: new Map<string, Study>() });

  /** Studies as a sorted array for the dropdown */
  studiesArray = computed(() =>
    Array.from(this.studiesMap().values()).sort((a, b) =>
      a.accession.localeCompare(b.accession),
    ),
  );

  /** The currently selected Study object */
  selectedStudy = computed<Study | undefined>(() =>
    this.studiesMap().get(this.selectedStudyAccession() ?? ''),
  );

  /** Files from the selected study in metadata */
  metadataFiles = toSignal(
    toObservable(this.selectedStudy).pipe(
      switchMap((study) =>
        study ? this.#metadataService.filesOfStudy(study) : of([]),
      ),
    ),
    { initialValue: [] as EmFile[] },
  );

  /** Files in the upload box */
  boxFiles = computed<FileUploadWithAccession[]>(() =>
    this.#uploadBoxService.boxFileUploads.value(),
  );

  // Derived mappings

  /** Auto-matched mappings from metadata accession to box file ID */
  autoMappings = computed<Map<string, string>>(() =>
    computeAutoMappings(
      this.metadataFiles(),
      this.boxFiles(),
      this.committedMappedField(),
    ),
  );

  /**
   * Effective mapping: manual entries override auto entries.
   * `null` values in manualMappings explicitly clear an auto-match.
   */
  effectiveMappings = computed<Map<string, string>>(() => {
    const auto = this.autoMappings();
    const manual = this.manualMappings();
    const result = new Map(auto);
    for (const [acc, boxId] of manual) {
      if (boxId === null) {
        result.delete(acc);
      } else {
        result.set(acc, boxId);
      }
    }
    return result;
  });

  /** Box file IDs that are not yet claimed by any mapping */
  unusedBoxFileIds = computed<Set<string>>(() => {
    const usedIds = new Set(this.effectiveMappings().values());
    return new Set(
      this.boxFiles()
        .filter((bf) => !usedIds.has(bf.id))
        .map((bf) => bf.id),
    );
  });

  // Stats

  /** Number of metadata files that have an effective mapping */
  mappedMetaCount = computed(
    () =>
      this.metadataFiles().filter((f) => this.effectiveMappings().has(f.accession))
        .length,
  );

  /** Number of metadata files without an effective mapping */
  unmappedMetaCount = computed(
    () => this.metadataFiles().length - this.mappedMetaCount(),
  );

  /** Number of auto-matched mappings not overridden by a manual entry */
  exactMatchCount = computed(() => {
    let count = 0;
    const auto = this.autoMappings();
    const manual = this.manualMappings();
    for (const [acc, boxId] of auto) {
      // still effectively mapped by auto (not overridden by manual)
      if (!manual.has(acc) || manual.get(acc) === boxId) count++;
    }
    return count;
  });

  /** Number of manually established mappings (different from auto) */
  manualMappingCount = computed(() => {
    let count = 0;
    const auto = this.autoMappings();
    const manual = this.manualMappings();
    for (const [acc, boxId] of manual) {
      if (boxId !== null && auto.get(acc) !== boxId) count++;
    }
    return count;
  });

  /** Number of box files not referenced by any mapping */
  unmappedBoxCount = computed(() => this.unusedBoxFileIds().size);

  // Table rows

  private readonly boxFileById = computed<Map<string, FileUploadWithAccession>>(() => {
    return new Map(this.boxFiles().map((bf) => [bf.id, bf]));
  });

  /** All rows (unfiltered) */
  mappingRows = computed<MappingRow[]>(() => {
    const effective = this.effectiveMappings();
    const auto = this.autoMappings();
    const manual = this.manualMappings();
    const byId = this.boxFileById();

    return this.metadataFiles().map((meta) => {
      const boxFileId = effective.get(meta.accession);
      const boxFile = boxFileId ? byId.get(boxFileId) : undefined;

      let mappingType: MappingRow['mappingType'] = 'none';
      if (boxFileId) {
        const manualEntry = manual.get(meta.accession);
        const isManuallySet =
          manualEntry !== undefined &&
          manualEntry !== null &&
          manualEntry !== auto.get(meta.accession);
        const isAutoMatch =
          auto.has(meta.accession) && auto.get(meta.accession) === boxFileId;
        mappingType = !isManuallySet && isAutoMatch ? 'exact' : 'manual';
      }

      return { metadataFile: meta, boxFile, mappingType };
    });
  });

  /** Rows filtered by the current filterText */
  filteredRows = computed<MappingRow[]>(() => {
    const filter = this.filterText().trim().toLowerCase();
    if (!filter) return this.mappingRows();
    return this.mappingRows().filter((row) => {
      const field = this.committedMappedField();
      const metaName = field ? (row.metadataFile[field] ?? '') : '';
      return (
        metaName.toLowerCase().includes(filter) ||
        (row.boxFile?.alias ?? '').toLowerCase().includes(filter)
      );
    });
  });

  // Autocomplete options for inline editor

  /** Options for the inline autocomplete, sorted with prefix matches first */
  autocompleteOptions = computed<FileUploadWithAccession[]>(() => {
    const unused = this.unusedBoxFileIds();
    const editingAcc = this.editingMetaAccession();
    const currentBoxId = editingAcc
      ? this.effectiveMappings().get(editingAcc)
      : undefined;
    const query = this.inlineInputValue().toLowerCase().trim();

    // Derive the metadata field value for this row so we can float
    // name-matching candidates to the top even when no text is typed.
    const field = this.committedMappedField();
    const editingMetaFile = editingAcc
      ? this.metadataFiles().find((f) => f.accession === editingAcc)
      : undefined;
    const metaValue =
      editingMetaFile && field ? (editingMetaFile[field] ?? '').toLowerCase() : '';

    const candidates = this.boxFiles().filter(
      (bf) =>
        (unused.has(bf.id) || bf.id === currentBoxId) &&
        (!query || bf.alias.toLowerCase().includes(query)),
    );

    return candidates.sort((a, b) => {
      const aAlias = a.alias.toLowerCase();
      const bAlias = b.alias.toLowerCase();
      // Tier 1: name-field exact match (or typed exact match) — absolute top
      const aNameMatch =
        (metaValue !== '' && aAlias === metaValue) ||
        (query !== '' && aAlias === query);
      const bNameMatch =
        (metaValue !== '' && bAlias === metaValue) ||
        (query !== '' && bAlias === query);
      if (aNameMatch !== bNameMatch) return aNameMatch ? -1 : 1;
      // Tier 2: currently-mapped file
      const aMapped = a.id === currentBoxId;
      const bMapped = b.id === currentBoxId;
      if (aMapped !== bMapped) return aMapped ? -1 : 1;
      // Tier 3: prefix matches when the user has typed something
      const aStarts = query !== '' && aAlias.startsWith(query);
      const bStarts = query !== '' && bAlias.startsWith(query);
      if (aStarts !== bStarts) return aStarts ? -1 : 1;
      return fileSortKey(a.alias).localeCompare(fileSortKey(b.alias));
    });
  });

  // Table datasource, sort, and paginator

  readonly tableDataSource = new MatTableDataSource<MappingRow>([]);
  readonly columns = ['metadataName', 'boxFileName'] as const;

  private readonly tableSort = viewChild(MatSort);
  private readonly tablePaginator = viewChild(MatPaginator);

  // Effects

  /** Keep table data in sync with filtered rows */
  #syncTableEffect = effect(() => {
    this.tableDataSource.data = this.filteredRows();
  });

  /** Assign paginator once it's available */
  #assignPaginatorEffect = effect(() => {
    const paginator = this.tablePaginator();
    if (paginator) this.tableDataSource.paginator = paginator;
  });

  /** Assign sort once it's available */
  #assignSortEffect = effect(() => {
    const sort = this.tableSort();
    if (sort) {
      this.tableDataSource.sort = sort;
      this.tableDataSource.sortingDataAccessor = (row, column) => {
        if (column === 'metadataName') {
          const field = this.committedMappedField();
          return fileSortKey(
            field ? (row.metadataFile[field] ?? undefined) : undefined,
          );
        }
        return fileSortKey(row.boxFile?.alias);
      };
      /*
       * MatSort.initialized fires during ngOnInit, before viewChild resolves.
       * By the time this effect runs, the initialized Subject has already emitted,
       * so the combineLatest inside MatTableDataSource never receives an initial
       * trigger and leaves the data unsorted. Emitting sortChange with the current
       * state (set via matSortActive/matSortDirection in the template) kicks off
       * the first sort pass through the custom sortingDataAccessor.
       */
      sort.sortChange.emit({ active: sort.active, direction: sort.direction });
    }
  });

  /** Persist mapping state whenever the three persistent signals change */
  #saveStateEffect = effect(() => {
    this.#mappingStateService.saveSnapshot(this.box().id, {
      studyAccession: this.selectedStudyAccession(),
      mappedField: this.committedMappedField(),
      manualMappings: Array.from(this.manualMappings()),
    });
  });

  /**
   * Watch pending field changes; if manual mappings exist, ask for confirmation
   * before committing, otherwise commit immediately.
   * A re-entry lock prevents a second dialog from opening while one is already
   * open (e.g. if manualMappings changes reactively during dialog lifetime).
   */
  #fieldChangeEffect = effect(() => {
    const pending = this.pendingMappedField();
    const committed = this.committedMappedField();
    if (pending === committed) return;
    if (this.#fieldChangeDialogOpen()) return;

    if (this.manualMappings().size === 0) {
      this.committedMappedField.set(pending);
      return;
    }

    this.#fieldChangeDialogOpen.set(true);
    const ref = this.#dialog.open<ConfirmDialogComponent, ConfirmDialogData, boolean>(
      ConfirmDialogComponent,
      {
        data: {
          title: 'Change mapped field',
          message:
            'Changing the mapped field will discard all manual mappings. Do you want to proceed?',
          confirmText: 'Change field',
          cancelText: 'Keep editing',
          confirmClass: 'button-error',
        },
      },
    );
    ref.afterClosed().subscribe((confirmed) => {
      this.#fieldChangeDialogOpen.set(false);
      if (confirmed) {
        this.manualMappings.set(new Map());
        this.committedMappedField.set(pending);
      } else {
        // revert dropdown to committed value
        this.pendingMappedField.set(committed);
      }
    });
  });

  // Lifecycle

  /** @inheritdoc */
  ngOnInit(): void {
    const snapshot = this.#mappingStateService.snapshotFor(this.box().id);
    if (snapshot) {
      this.selectedStudyAccession.set(snapshot.studyAccession);
      this.committedMappedField.set(snapshot.mappedField);
      this.pendingMappedField.set(snapshot.mappedField);
      this.manualMappings.set(new Map(snapshot.manualMappings));
    }
  }

  // Row editing

  /**
   * Open the inline editor for a given row.
   * @param row - the mapping row to edit
   */
  startEditing(row: MappingRow): void {
    this.editingMetaAccession.set(row.metadataFile.accession);
    this.inlineInputValue.set(row.boxFile?.alias ?? '');
  }

  /**
   * Commit the inline editor value for a given row.
   * Accepts the entered alias if it matches an unused box file (or the current
   * mapping). An empty string explicitly clears the mapping.
   * Invalid input silently reverts.
   * @param row - the mapping row being edited
   */
  commitInlineEdit(row: MappingRow): void {
    const alias = this.inlineInputValue().trim();
    const acc = row.metadataFile.accession;

    if (alias === '') {
      // Explicitly clear the mapping
      const updated = new Map(this.manualMappings());
      updated.set(acc, null);
      this.manualMappings.set(updated);
    } else {
      // Find a matching box file
      const lower = alias.toLowerCase();
      const exact = this.boxFiles().find((bf) => bf.alias === alias);
      const caseMatches = !exact
        ? this.boxFiles().filter((bf) => bf.alias.toLowerCase() === lower)
        : [];
      const match = exact ?? (caseMatches.length === 1 ? caseMatches[0] : undefined);

      if (match) {
        const isUnused = this.unusedBoxFileIds().has(match.id);
        const isCurrent = this.effectiveMappings().get(acc) === match.id;

        if (isUnused || isCurrent) {
          const updated = new Map(this.manualMappings());
          updated.set(acc, match.id);
          this.manualMappings.set(updated);
        }
        // else: box file is already mapped elsewhere — silently revert
      }
      // else: alias not found in box — silently revert
    }

    this.editingMetaAccession.set(null);
  }

  // Actions

  /**
   * Reset manual mappings without confirmation.
   * Auto-mappings are recomputed automatically.
   */
  onReset(): void {
    this.manualMappings.set(new Map());
    this.#notificationService.showInfo('Manual mappings have been reset.');
  }

  /**
   * Cancel the mapping form: clear the field selection and manual mappings,
   * keep the study selection, and navigate back.
   */
  onCancel(): void {
    this.committedMappedField.set(undefined);
    this.pendingMappedField.set(undefined);
    this.filterText.set('');
    this.manualMappings.set(new Map());
    this.editingMetaAccession.set(null);
    this.inlineInputValue.set('');
    this.#navigationService.back(['/upload-box-manager']);
  }

  /** Reset all form state back to initial values and clear the saved snapshot */
  #resetForm(): void {
    this.#mappingStateService.clearSnapshot(this.box().id);
    this.selectedStudyAccession.set(undefined);
    this.committedMappedField.set(undefined);
    this.pendingMappedField.set(undefined);
    this.filterText.set('');
    this.manualMappings.set(new Map());
    this.editingMetaAccession.set(null);
    this.inlineInputValue.set('');
  }

  /** Clear the selected study and all dependent mapping state */
  onChangeStudy(): void {
    if (this.manualMappings().size > 0) {
      const ref = this.#dialog.open<ConfirmDialogComponent, ConfirmDialogData, boolean>(
        ConfirmDialogComponent,
        {
          data: {
            title: 'Change study',
            message:
              'You have established manual mappings that will be lost if you select a different study. Do you want to proceed?',
            confirmText: 'Change study',
            cancelText: 'Keep editing',
            confirmClass: 'button-error',
          },
        },
      );
      ref.afterClosed().subscribe((confirmed) => {
        if (confirmed) this.#resetForm();
      });
    } else {
      this.#resetForm();
    }
  }

  /**
   * Open the confirmation dialog and, if confirmed, submit the mapping.
   */
  onConfirmAndArchive(): void {
    const effective = this.effectiveMappings();
    const boxFiles = this.boxFiles();
    const metaFiles = this.metadataFiles();
    const field = this.committedMappedField();

    const unmappedBoxFileIds = this.unusedBoxFileIds();
    const unmappedBoxFileAliases = boxFiles
      .filter((bf) => unmappedBoxFileIds.has(bf.id))
      .map((bf) => bf.alias);

    const unmappedMetaFileNames = metaFiles
      .filter((mf) => !effective.has(mf.accession))
      .map((mf) => (field ? (mf[field] ?? mf.accession) : mf.accession));

    const ref = this.#dialog.open<
      UploadBoxMappingConfirmDialogComponent,
      MappingConfirmDialogData,
      boolean
    >(UploadBoxMappingConfirmDialogComponent, {
      data: { unmappedBoxFileAliases, unmappedMetaFileNames },
      width: 'clamp(24rem, 90vw, 42rem)',
    });

    ref.afterClosed().subscribe((confirmed) => {
      if (!confirmed) return;
      this.#submitMapping(effective);
    });
  }

  /**
   * Build the request and POST it to the backend.
   * @param effective - the final mapping to submit
   */
  #submitMapping(effective: Map<string, string>): void {
    const studyId = this.selectedStudyAccession();
    if (!studyId) return;

    const mapping: Record<string, string> = {};
    for (const [accession, boxFileId] of effective) {
      mapping[accession] = boxFileId;
    }

    this.isSubmitting.set(true);
    const box = this.box();
    this.#uploadBoxService
      .submitFileMapping(box.id, {
        box_version: box.version,
        study_id: studyId,
        mapping,
      })
      .pipe(
        catchError(() => throwError(() => 'mapping' as const)),
        concatMap(() =>
          this.#uploadBoxService
            .archiveUploadBox(box.id, box.version + 1)
            .pipe(catchError(() => throwError(() => 'archival' as const))),
        ),
      )
      .subscribe({
        next: () => {
          this.isSubmitting.set(false);
          this.#mappingStateService.clearSnapshot(box.id);
          this.#notificationService.showSuccess(
            'File mapping submitted and upload box archived successfully.',
          );
          this.archived.emit();
        },
        error: (phase: 'mapping' | 'archival') => {
          this.isSubmitting.set(false);
          this.#notificationService.showError(
            phase === 'archival'
              ? 'Mapping was submitted but archival failed.'
              : 'Failed to submit the file mapping.',
          );
        },
      });
  }

  /**
   * Display function for the MatAutocomplete on the box file field.
   * @param file - the selected file upload object, or a plain string from typing
   * @returns the alias string to display
   */
  displayBoxFileAlias(file: FileUploadWithAccession | string | undefined): string {
    if (!file) return '';
    if (typeof file === 'string') return file;
    return file.alias;
  }

  /** Whether the "Confirm and archive" button should be enabled */
  canConfirmAndArchive = computed<boolean>(
    () =>
      !!this.selectedStudyAccession() &&
      !!this.committedMappedField() &&
      !this.isSubmitting(),
  );

  /** Whether the Reset button should be enabled */
  canReset = computed<boolean>(() => this.manualMappings().size > 0);
}
