/**
 * Detail view for a single upload box in the upload box manager.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DatePipe as CommonDatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  input,
  OnInit,
  signal,
  viewChild,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIcon } from '@angular/material/icon';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { Router, RouterLink } from '@angular/router';

import { DisplayUser, UserService } from '@app/auth/services/user';
import { Capitalise } from '@app/shared/pipes/capitalise-pipe';
import { DatePipe } from '@app/shared/pipes/date-pipe';
import { ParseBytes } from '@app/shared/pipes/parse-bytes-pipe';
import { ConfirmationService } from '@app/shared/services/confirmation';
import { NavigationTrackingService } from '@app/shared/services/navigation';
import { NotificationService } from '@app/shared/services/notification';
import {
  DEFAULT_TIME_ZONE,
  FRIENDLY_DATE_FORMAT,
} from '@app/shared/utils/date-formats';
import {
  ResearchDataUploadBox,
  UploadBoxState,
  UploadBoxStateClass,
} from '@app/upload/models/box';
import {
  FileUploadState,
  FileUploadWithAccession,
} from '@app/upload/models/file-upload';
import { UploadGrant } from '@app/upload/models/grant';
import { FileUploadStatePipe } from '@app/upload/pipes/file-upload-state-pipe';
import { UploadBoxService } from '@app/upload/services/upload-box';
import { UploadBoxMappingComponent } from '../upload-box-mapping/upload-box-mapping';

/**
 * Detail view component for managing an individual upload box.
 * Displays box metadata, upload grants (placeholder), and files (placeholder).
 */
@Component({
  selector: 'app-upload-box-manager-detail',
  imports: [
    DatePipe,
    MatButtonModule,
    MatCardModule,
    MatIcon,
    MatPaginatorModule,
    MatTableModule,
    RouterLink,
    Capitalise,
    ParseBytes,
    FileUploadStatePipe,
    UploadBoxMappingComponent,
  ],
  providers: [CommonDatePipe],
  templateUrl: './upload-box-manager-detail.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UploadBoxManagerDetailComponent implements OnInit {
  #uploadBoxService = inject(UploadBoxService);
  #userService = inject(UserService);
  #location = inject(NavigationTrackingService);
  #notificationService = inject(NotificationService);
  #confirmationService = inject(ConfirmationService);
  #router = inject(Router);
  #isBackNavigation = this.#router.getCurrentNavigation()?.trigger === 'popstate';

  /** Route parameter bound automatically via withComponentInputBinding. */
  id = input.required<string>();

  /** Whether to apply the forward view transition animation (slide from right). */
  showTransition = false;

  /** Whether to apply the back view transition animation (slide from left). */
  showBackTransition = false;

  #singleBox = this.#uploadBoxService.uploadBox;
  #allBoxes = this.#uploadBoxService.uploadBoxes;

  #cachedBox = signal<ResearchDataUploadBox | undefined>(undefined);

  /**
   * The upload box to display.
   * Prefer the live single-box resource for the current ID when available,
   * and fall back to the list-derived cache for initial rendering.
   */
  uploadBox = computed<ResearchDataUploadBox | undefined>(() => {
    const id = this.id();
    const single = this.#singleBox.error() ? undefined : this.#singleBox.value();
    if (single && single.id === id) {
      return single;
    }
    return this.#cachedBox();
  });

  /** Whether the upload box data is currently being loaded. */
  isLoading = computed<boolean>(
    () => !this.#cachedBox() && this.#singleBox.isLoading(),
  );

  /** Any error that occurred while loading the upload box. */
  error = computed<undefined | 'not found' | 'other'>(() => {
    if (this.#cachedBox()) return undefined;
    const err = this.#singleBox.error();
    if (!err) return undefined;
    return (err as HttpErrorResponse)?.status === 404 ? 'not found' : 'other';
  });

  /** The human-readable storage location label for this box. */
  storageLocationLabel = computed<string>(() =>
    this.#uploadBoxService.getStorageLocationLabel(
      this.uploadBox()?.storage_alias ?? '',
    ),
  );

  /** The user who last changed this box, undefined while loading, null on error. */
  changedBy = signal<DisplayUser | null | undefined>(undefined);

  #changedByFetcher = this.#userService.createUserFetcher();

  #loadChangedByEffect = effect(() => {
    const changedById = this.uploadBox()?.changed_by;
    if (!changedById) {
      this.changedBy.set(undefined);
      return;
    }
    const changedByResource = this.#changedByFetcher.resource;
    if (changedByResource.isLoading()) return;
    if (changedByResource.error()) {
      this.changedBy.set(null);
      return;
    }
    const changedByUser = changedByResource.value();
    if (changedByUser && changedByUser.id === changedById) {
      this.changedBy.set(changedByUser);
      return;
    }
    this.#changedByFetcher.load(changedById);
  });

  #loadFileUploadsEffect = effect(() => {
    const box = this.uploadBox();
    if (box && box.file_count > 0 && !this.#cachedBox()) {
      this.#uploadBoxService.loadFileUploadsForBox(box.id);
    }
  });

  /** Human-readable date format for last change. */
  readonly friendlyDateFormat = FRIENDLY_DATE_FORMAT;

  /** Timezone for date display. */
  readonly timeZone = DEFAULT_TIME_ZONE;

  /** Map from UploadBoxState to CSS class. */
  readonly stateClass = UploadBoxStateClass;

  /** Placeholder columns for the upload grants table. */
  readonly grantColumns = ['grantee', 'status', 'validity', 'details'];

  /** Columns for the file uploads table. */
  fileColumns = computed<string[]>(() => {
    const state = this.uploadBox()?.state;
    if (state === UploadBoxState.archived) {
      return ['alias', 'accession', 'size', 'uploaded'];
    }
    const columns = ['alias', 'status', 'size', 'uploaded'];
    // Files can only be deleted while the box is still open for uploads.
    if (state === UploadBoxState.open) {
      columns.push('delete');
    }
    return columns;
  });

  /** The upload grants for this box. */
  grants = computed<UploadGrant[]>(() => this.#uploadBoxService.boxGrants.value());

  /** MatTableDataSource for paginated file uploads. */
  fileUploadsDataSource = new MatTableDataSource<FileUploadWithAccession>();

  private readonly fileUploadsPaginator = viewChild(MatPaginator);

  #syncFileUploadsEffect = effect(() => {
    this.fileUploadsDataSource.data = this.#uploadBoxService.boxFileUploads.value();
  });

  #assignPaginatorEffect = effect(() => {
    const paginator = this.fileUploadsPaginator();
    if (paginator) {
      this.fileUploadsDataSource.paginator = paginator;
    }
  });

  /**
   * Check if an upload grant is currently active.
   * @param grant - the upload grant to check
   * @returns true if the grant is within its valid period
   */
  isGrantActive(grant: UploadGrant): boolean {
    const today = new Date().toISOString().slice(0, 10);
    return grant.valid_from <= today && today <= grant.valid_until;
  }

  /**
   * Handle the archived event from the mapping component by clearing the cached
   * box and reloading fresh data, so the UI transitions out of the locked state.
   */
  onBoxArchived(): void {
    this.#cachedBox.set(undefined);
    const id = this.id();
    if (id) this.#uploadBoxService.loadUploadBox(id);
  }

  /**
   * File states that may be deleted: still being uploaded (init), re-encrypted
   * (inbox), or already re-encrypted (interrogated).
   */
  readonly #deletableFileStates: readonly FileUploadState[] = [
    'init',
    'inbox',
    'interrogated',
  ];

  /**
   * Whether the given file may be deleted. Only files in a deletable state
   * within an open box can be removed.
   * @param file - the file upload to check
   * @returns true if the file can be deleted
   */
  canDeleteFile(file: FileUploadWithAccession): boolean {
    return (
      this.uploadBox()?.state === UploadBoxState.open &&
      this.#deletableFileStates.includes(file.state)
    );
  }

  /**
   * Delete a file upload from the box. Files that are still being uploaded
   * (init) are deleted right away; files that are being re-encrypted (inbox)
   * or already re-encrypted (interrogated) require an extra confirmation first.
   * @param file - the file upload to delete
   */
  deleteFile(file: FileUploadWithAccession): void {
    const box = this.uploadBox();
    if (!box) return;
    if (file.state !== 'init') {
      this.#confirmationService.confirm({
        title: 'Confirm file deletion',
        message:
          `<p>Please confirm that the file <strong>${file.alias}</strong> shall be ` +
          '<strong>deleted</strong> from this upload box.</p>',
        cancelText: 'Cancel',
        confirmText: 'Delete file',
        confirmClass: 'error',
        callback: (confirmed) => {
          if (confirmed) this.#performFileDeletion(box.id, file);
        },
      });
      return;
    }
    this.#performFileDeletion(box.id, file);
  }

  /**
   * Perform the actual file deletion request and report the outcome.
   * @param boxId - the ID of the upload box the file belongs to
   * @param file - the file upload to delete
   */
  #performFileDeletion(boxId: string, file: FileUploadWithAccession): void {
    this.#uploadBoxService.deleteFileUpload(boxId, file).subscribe({
      next: () =>
        this.#notificationService.showSuccess(
          `The file "${file.alias}" has been deleted.`,
        ),
      error: () =>
        this.#notificationService.showError(
          `The file "${file.alias}" could not be deleted.`,
        ),
    });
  }

  /**
   * Navigate to the new upload grant creation page.
   */
  addGrant(): void {
    const boxId = this.id();
    if (boxId) this.#router.navigate(['/upload-box-manager', boxId, 'grant', 'new']);
  }

  /** Notify error effect for single-box fetch failures. */
  #errorEffect = effect(() => {
    if (this.error() === 'other') {
      this.#notificationService.showError('Error retrieving upload box details.');
    }
  });

  /**
   * On initialization, start the slide-in transition and load box data.
   * Uses the list cache if available, otherwise fetches the single box.
   */
  ngOnInit(): void {
    if (this.#isBackNavigation) {
      this.showBackTransition = true;
      setTimeout(() => (this.showBackTransition = false), 300);
    } else {
      this.showTransition = true;
      setTimeout(() => (this.showTransition = false), 300);
    }

    const id = this.id();
    this.#uploadBoxService.loadStorageLabels();
    if (id) {
      this.#uploadBoxService.loadBoxGrants(id);
      // Has the single box already been fetched individually?
      const single = this.#singleBox.error() ? undefined : this.#singleBox.value();
      if (single && single.id === id) {
        this.#cachedBox.set(single);
        // Load file uploads if the box has files
        if (single.file_count > 0) {
          this.#uploadBoxService.loadFileUploadsForBox(id);
        }
      } else {
        // Has it been loaded as part of the full list?
        const fromList = this.#allBoxes().find((b) => b.id === id);
        if (fromList) {
          this.#cachedBox.set(fromList);
          // Load file uploads if the box has files
          if (fromList.file_count > 0) {
            this.#uploadBoxService.loadFileUploadsForBox(id);
          }
        } else {
          // Neither — fetch it individually
          this.#uploadBoxService.loadUploadBox(id);
        }
      }

      // Always load the single-box resource as source of truth so local state
      // updates (e.g. archived transition) are reflected in this detail view.
      this.#uploadBoxService.loadUploadBox(id);
    }
  }

  /**
   * Navigate back to the upload box manager list.
   */
  goBack(): void {
    this.showTransition = true;
    setTimeout(() => {
      this.#location.back(['/upload-box-manager']);
    });
  }
}
