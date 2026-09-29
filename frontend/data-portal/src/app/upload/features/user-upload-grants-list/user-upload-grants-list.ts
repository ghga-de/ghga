/**
 * Component that lists the current user's open Research Data Upload Boxes.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { ConfirmationService } from '@app/shared/services/confirmation';
import { NotificationService } from '@app/shared/services/notification';
import { StencilComponent } from '@app/shared/ui/stencil/stencil/stencil';
import { UploadBoxState } from '@app/upload/models/box';
import { GrantWithBoxInfo } from '@app/upload/models/grant';
import { UploadBoxService } from '@app/upload/services/upload-box';
import {
  describeIncompleteOrFailedConflict,
  IncompleteOrFailedConflict,
  incompleteOrFailedConflictTitle,
  parseIncompleteOrFailedConflict,
} from '@app/upload/utils/box-conflict';
import { UserUploadBoxDetailsDialogComponent } from '@app/upload/features/user-upload-box-details-dialog/user-upload-box-details-dialog';
// eslint-disable-next-line boundaries/dependencies
import { UploadWorkPackageDialogComponent } from '@app/work-packages/features/upload-work-package-dialog/upload-work-package-dialog';

/**
 * Shows the current user's open Research Data Upload Boxes (RDUBs).
 * For each open box the user can create an upload token (placeholder) or submit the box.
 */
@Component({
  selector: 'app-user-upload-grants-list',
  imports: [StencilComponent, MatIconModule, MatButtonModule],
  templateUrl: './user-upload-grants-list.html',
})
export class UserUploadGrantsListComponent implements OnInit {
  #uploadBoxService = inject(UploadBoxService);
  #confirmation = inject(ConfirmationService);
  #dialog = inject(MatDialog);
  #notification = inject(NotificationService);

  isLoading = this.#uploadBoxService.userGrants.isLoading;
  protected hasError = this.#uploadBoxService.userGrants.error;

  /**
   * Fetch the grants again whenever the account page is opened. The underlying
   * resource is triggered by the logged-in user alone, so without this it would
   * be fetched once per session and grants created afterwards (by a data
   * steward, possibly the user themselves) would never show up.
   */
  ngOnInit(): void {
    this.#uploadBoxService.reloadUserGrants();
  }

  /**
   * Fetch the grants again on request. Box states and titles are changed by data
   * stewards, and new grants can be issued while the account page is open.
   */
  refresh(): void {
    this.#uploadBoxService.reloadUserGrants();
  }

  /** Open upload grants filtered by state and deduplicated by upload box ID. */
  protected openGrants = computed(() => {
    const openGrants = this.#uploadBoxService.userGrants
      .value()
      .filter((grant) => grant.box_state === UploadBoxState.open);

    const uniqueByBoxId = new Map<string, GrantWithBoxInfo>();
    for (const grant of openGrants) {
      if (!uniqueByBoxId.has(grant.box_id)) {
        uniqueByBoxId.set(grant.box_id, grant);
      }
    }

    return Array.from(uniqueByBoxId.values());
  });

  /** ID of the box currently being submitted, to disable the button while in flight. */
  protected submittingBoxId = signal<string | null>(null);

  /**
   * Open a read-only dialog showing the details and files of the box.
   * @param grant - the upload grant with box information
   */
  viewDetails(grant: GrantWithBoxInfo): void {
    this.#dialog.open(UserUploadBoxDetailsDialogComponent, {
      data: grant,
      width: 'clamp(40em, 85vw, 64em)',
      maxWidth: 'calc(100vw - 2rem)',
      // Focus the dialog heading instead of the first tabbable element, which
      // would otherwise be the first sortable column header of the files table.
      autoFocus: 'first-heading',
    });
  }

  /**
   * Open the upload token creation dialog for a selected upload grant.
   * @param grant - the upload grant with box information
   */
  createToken(grant: GrantWithBoxInfo): void {
    this.#dialog.open(UploadWorkPackageDialogComponent, {
      data: grant,
      width: '64rem',
      maxWidth: '96vw',
    });
  }

  /**
   * Ask for confirmation and, on approval, submit the upload box (set state to locked).
   * @param grant - the grant whose upload box should be submitted
   */
  submitBox(grant: GrantWithBoxInfo): void {
    this.#confirmation.confirm({
      title: 'Submit upload box?',
      message:
        'Submitting closes the upload box. ' +
        'This action can only be reversed by a data steward. ' +
        'Are you sure you want to proceed?',
      confirmText: 'Submit',
      callback: (confirmed) => {
        if (!confirmed) return;
        this.#submitBox(grant, false);
      },
    });
  }

  /**
   * Submit the upload box (set state to locked). When the backend rejects the
   * submission with a 409 because some uploads are still incomplete or failed
   * re-encryption, ask the user whether to force it and retry once with force=true.
   * @param grant - the grant whose upload box should be submitted
   * @param force - whether to submit despite incomplete or failed uploads
   */
  #submitBox(grant: GrantWithBoxInfo, force: boolean): void {
    this.submittingBoxId.set(grant.box_id);
    this.#uploadBoxService
      .lockUploadBox(grant.box_id, grant.box_version, force)
      .subscribe({
        next: () => {
          this.submittingBoxId.set(null);
          this.#notification.showSuccess(
            'The upload box has been submitted successfully.',
          );
        },
        error: (err: unknown) => {
          // Offer the force option only on the first attempt and only when the
          // conflict is specifically caused by incomplete or failed uploads. A
          // forced retry that still fails falls through to the generic message.
          const conflict = force ? null : parseIncompleteOrFailedConflict(err);
          if (conflict) {
            this.#confirmForceSubmit(grant, conflict);
          } else {
            this.submittingBoxId.set(null);
            this.#notification.showError(
              'Failed to submit the upload box. Please try again.',
            );
          }
        },
      });
  }

  /**
   * Ask the user whether to submit despite incomplete or failed uploads. On
   * confirmation, retry the submission with force=true; otherwise leave the box open.
   * @param grant - the grant whose upload box should be submitted
   * @param conflict - the file uploads that blocked the submission
   */
  #confirmForceSubmit(
    grant: GrantWithBoxInfo,
    conflict: IncompleteOrFailedConflict,
  ): void {
    const reason = describeIncompleteOrFailedConflict(conflict, 'Submission');
    // Failed files cannot be fixed by the submitter, so say who resolves them.
    const resolution = conflict.needAttention.length
      ? ' A Data Steward will have to resolve the failed files before the box can be archived.'
      : '';
    this.#confirmation.confirm({
      title: incompleteOrFailedConflictTitle(conflict),
      message: `${reason}${resolution} Do you want to submit anyway?`,
      confirmText: 'Submit anyway',
      callback: (confirmed) => {
        if (!confirmed) {
          this.submittingBoxId.set(null);
          return;
        }
        this.#submitBox(grant, true);
      },
    });
  }
}
