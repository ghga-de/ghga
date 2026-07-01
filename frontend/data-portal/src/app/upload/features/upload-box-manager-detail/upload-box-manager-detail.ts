/**
 * Detail view for a single upload box in the upload box manager.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DatePipe as CommonDatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import {
  Component,
  computed,
  effect,
  inject,
  input,
  OnInit,
  signal,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog } from '@angular/material/dialog';
import { MatIcon } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
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
import { UploadBoxService } from '@app/upload/services/upload-box';
import { UploadBoxEditDetailsDialogComponent } from '../upload-box-edit-details-dialog/upload-box-edit-details-dialog';
import { UploadBoxFilesTableComponent } from '../upload-box-files-table/upload-box-files-table';
import { UploadBoxMappingComponent } from '../upload-box-mapping/upload-box-mapping';

/** An upload grant annotated with whether it is currently active. */
interface GrantWithStatus extends UploadGrant {
  active: boolean;
}

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
    MatTableModule,
    MatTooltipModule,
    RouterLink,
    Capitalise,
    ParseBytes,
    UploadBoxFilesTableComponent,
    UploadBoxMappingComponent,
  ],
  providers: [CommonDatePipe, ParseBytes],
  templateUrl: './upload-box-manager-detail.html',
})
export class UploadBoxManagerDetailComponent implements OnInit {
  #uploadBoxService = inject(UploadBoxService);
  #userService = inject(UserService);
  #location = inject(NavigationTrackingService);
  #notificationService = inject(NotificationService);
  #confirmationService = inject(ConfirmationService);
  #parseBytes = inject(ParseBytes);
  #dialog = inject(MatDialog);
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

  /**
   * The upload grants for this box, each annotated with whether it is currently
   * active. Computed once per grant change (rather than per change-detection
   * cycle) so the template can bind to `grant.active` instead of calling a method.
   */
  grants = computed<GrantWithStatus[]>(() => {
    const today = new Date().toISOString().slice(0, 10);
    return this.#uploadBoxService.boxGrants.value().map((grant) => ({
      ...grant,
      active: grant.valid_from <= today && today <= grant.valid_until,
    }));
  });

  /** The file uploads contained in this box. */
  fileUploads = computed<FileUploadWithAccession[]>(() =>
    this.#uploadBoxService.boxFileUploads.value(),
  );

  /** Whether a box state change (lock or reopen) is currently in flight. */
  isChangingState = signal<boolean>(false);

  /**
   * Ask for confirmation and, on approval, lock the upload box.
   */
  lockBox(): void {
    const box = this.uploadBox();
    if (!box) return;
    this.#confirmationService.confirm({
      title: 'Lock upload box?',
      message:
        'Locking the box prevents further file uploads by its users. ' +
        'Are you sure you want to proceed?',
      confirmText: 'Lock the box',
      callback: (confirmed) => {
        if (confirmed) this.#lockBox(box, false);
      },
    });
  }

  /**
   * Lock the upload box (set state to locked). When the backend rejects the
   * request with a 409 because some uploads are still incomplete, ask the
   * user whether to force it and retry once with force=true.
   * @param box - the upload box to lock
   * @param force - whether to lock despite incomplete uploads
   */
  #lockBox(box: ResearchDataUploadBox, force: boolean): void {
    this.isChangingState.set(true);
    this.#uploadBoxService.lockUploadBox(box.id, box.version, force).subscribe({
      next: () => {
        this.isChangingState.set(false);
        this.#notificationService.showSuccess('The upload box has been locked.');
      },
      error: (err: unknown) => {
        // Offer the force option only on the first attempt and only when the
        // conflict is specifically caused by incomplete uploads. A forced
        // retry that still fails falls through to the generic message.
        const incompleteUploads = force ? null : this.#incompleteUploads(err);
        if (incompleteUploads) {
          this.#confirmForceLock(box, incompleteUploads.length);
        } else {
          this.isChangingState.set(false);
          this.#notificationService.showError(
            'Failed to lock the upload box. Please try again.',
          );
        }
      },
    });
  }

  /**
   * Extract the incomplete uploads reported by a 409 locking conflict, which
   * the user may override by forcing the lock.
   * @param err - the error thrown by the lock request
   * @returns the incomplete uploads, or null if this is not such a conflict
   */
  #incompleteUploads(err: unknown): unknown[] | null {
    const response = err as HttpErrorResponse;
    const data: unknown = response?.error?.data;
    if (response?.status !== 409 || !data || typeof data !== 'object') return null;
    const uploads = (data as { incomplete_uploads?: unknown }).incomplete_uploads;
    return Array.isArray(uploads) ? uploads : null;
  }

  /**
   * Ask the user whether to lock despite incomplete uploads. On confirmation,
   * retry the lock with force=true; otherwise leave the box open.
   * @param box - the upload box to lock
   * @param count - the number of still-incomplete file uploads
   */
  #confirmForceLock(box: ResearchDataUploadBox, count: number): void {
    const [are, uploads] = count === 1 ? ['is', 'upload'] : ['are', 'uploads'];
    this.#confirmationService.confirm({
      title: 'Incomplete uploads detected!',
      message: `Locking failed because there ${are} still ${count} incomplete file ${uploads}. Do you want to lock the box anyway?`,
      confirmText: 'Lock anyway',
      callback: (confirmed) => {
        if (!confirmed) {
          this.isChangingState.set(false);
          return;
        }
        this.#lockBox(box, true);
      },
    });
  }

  /**
   * Ask for confirmation and, on approval, reopen the locked upload box.
   */
  openBox(): void {
    const box = this.uploadBox();
    if (!box) return;
    this.#confirmationService.confirm({
      title: 'Reopen upload box?',
      message:
        'Reopening the box allows its users to upload files again. ' +
        'Are you sure you want to proceed?',
      confirmText: 'Open the box',
      callback: (confirmed) => {
        if (!confirmed) return;
        this.isChangingState.set(true);
        this.#uploadBoxService.openUploadBox(box.id, box.version).subscribe({
          next: () => {
            this.isChangingState.set(false);
            this.#notificationService.showSuccess(
              'The upload box has been opened again.',
            );
          },
          error: () => {
            this.isChangingState.set(false);
            this.#notificationService.showError(
              'Failed to open the upload box. Please try again.',
            );
          },
        });
      },
    });
  }

  /**
   * Whether the upload box can be deleted. Archived boxes cannot be deleted by
   * the backend, so the delete button is disabled for them.
   */
  canDeleteBox = computed<boolean>(
    () => this.uploadBox()?.state !== UploadBoxState.archived,
  );

  /**
   * Ask for confirmation and, on approval, delete the upload box and all its
   * files. For a non-empty box, the confirmation states how many files (and
   * their total size) will be removed; for an empty box it only warns that the
   * action cannot be undone.
   */
  deleteBox(): void {
    const box = this.uploadBox();
    if (!box || box.state === UploadBoxState.archived) return;
    const message =
      box.file_count > 0
        ? `<p>This box currently contains <strong>${box.file_count} ` +
          `file${box.file_count === 1 ? '' : 's'}</strong> with a total size of ` +
          `<strong>${this.#parseBytes.transform(box.size)}</strong>.</p>` +
          '<p>Deleting the box will <strong>permanently remove all files</strong> ' +
          'it contains. This action <strong>cannot be undone</strong>.</p>'
        : '<p>This box is currently empty. Deleting it ' +
          '<strong>cannot be undone</strong>.</p>';
    this.#confirmationService.confirm({
      title: 'Delete upload box?',
      message,
      cancelText: 'Cancel',
      confirmText: 'Delete the box',
      confirmClass: 'error',
      callback: (confirmed) => {
        if (confirmed) this.#deleteBox(box);
      },
    });
  }

  /**
   * Perform the actual box deletion request, report the outcome and, on success,
   * navigate back to the upload box list.
   * @param box - the upload box to delete
   */
  #deleteBox(box: ResearchDataUploadBox): void {
    this.isChangingState.set(true);
    this.#uploadBoxService.deleteUploadBox(box.id, box.version).subscribe({
      next: () => {
        this.isChangingState.set(false);
        this.#notificationService.showSuccess('The upload box has been deleted.');
        this.goBack();
      },
      error: () => {
        this.isChangingState.set(false);
        this.#notificationService.showError(
          'Failed to delete the upload box. Please try again.',
        );
      },
    });
  }

  /**
   * Open a dialog to edit the box details (title, description, size limit).
   */
  editDetails(): void {
    const box = this.uploadBox();
    if (!box) return;
    const ref = this.#dialog.open(UploadBoxEditDetailsDialogComponent, {
      data: box,
      width: 'clamp(40em, 85vw, 64em)',
      maxWidth: 'calc(100vw - 2rem)',
    });
    ref.afterClosed().subscribe((updatedBoxId: string | undefined) => {
      if (!updatedBoxId) return;
      this.#notificationService.showSuccess(
        'The upload box details have been updated.',
      );
    });
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
   * Bound predicate passed to the files table so it can decide, per file,
   * whether to render a delete button.
   * @param file - the file upload to check
   * @returns true if the file can be deleted
   */
  readonly canDeleteFileFn = (file: FileUploadWithAccession): boolean =>
    this.canDeleteFile(file);

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
