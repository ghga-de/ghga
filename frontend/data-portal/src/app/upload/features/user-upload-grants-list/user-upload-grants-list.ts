/**
 * Component that lists the current user's open Research Data Upload Boxes.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpErrorResponse } from '@angular/common/http';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  signal,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { ConfirmationService } from '@app/shared/services/confirmation';
import { NotificationService } from '@app/shared/services/notification';
import { StencilComponent } from '@app/shared/ui/stencil/stencil/stencil';
import { UploadBoxState } from '@app/upload/models/box';
import { GrantWithBoxInfo } from '@app/upload/models/grant';
import { UploadBoxService } from '@app/upload/services/upload-box';
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
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UserUploadGrantsListComponent {
  #uploadBoxService = inject(UploadBoxService);
  #confirmation = inject(ConfirmationService);
  #dialog = inject(MatDialog);
  #notification = inject(NotificationService);

  protected isLoading = this.#uploadBoxService.userGrants.isLoading;
  protected hasError = this.#uploadBoxService.userGrants.error;

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
   * submission with a 409 because some uploads are still incomplete, ask the
   * user whether to force it and retry once with force=true.
   * @param grant - the grant whose upload box should be submitted
   * @param force - whether to submit despite incomplete uploads
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
          // conflict is specifically caused by incomplete uploads. A forced
          // retry that still fails falls through to the generic message.
          const incompleteUploads = force ? null : this.#incompleteUploads(err);
          if (incompleteUploads) {
            this.#confirmForceSubmit(grant, incompleteUploads.length);
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
   * Extract the incomplete uploads reported by a 409 submission conflict, which
   * the user may override by forcing the submission.
   * @param err - the error thrown by the submission request
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
   * Ask the user whether to submit despite incomplete uploads. On confirmation,
   * retry the submission with force=true; otherwise leave the box open.
   * @param grant - the grant whose upload box should be submitted
   * @param count - the number of still-incomplete file uploads
   */
  #confirmForceSubmit(grant: GrantWithBoxInfo, count: number): void {
    const [are, uploads] = count === 1 ? ['is', 'upload'] : ['are', 'uploads'];
    this.#confirmation.confirm({
      title: 'Incomplete uploads detected!',
      message: `Submission failed because there ${are} still ${count} incomplete file ${uploads}. Do you want to submit anyway?`,
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
