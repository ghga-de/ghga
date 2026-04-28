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
  fileColumns = computed<string[]>(() =>
    this.uploadBox()?.state === UploadBoxState.archived
      ? ['alias', 'accession', 'size', 'uploaded']
      : ['alias', 'status', 'size', 'uploaded'],
  );

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
   * Get the CSS class for a file upload status.
   * @param state - the file upload state
   * @returns the CSS class for the state
   */
  getFileStatusClass(state: FileUploadState): string {
    switch (state) {
      case 'interrogated':
        return 'text-success';
      case 'archived':
        return 'text-gray-600';
      case 'failed':
      case 'cancelled':
        return 'text-error';
      case 'init':
      case 'inbox':
      case 'awaiting_archival':
      default:
        return 'text-warning';
    }
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
