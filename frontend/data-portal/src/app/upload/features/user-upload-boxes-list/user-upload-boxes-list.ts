/**
 * Component that lists the current user's open Research Data Upload Boxes.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { ConfirmationService } from '@app/shared/services/confirmation';
import { NotificationService } from '@app/shared/services/notification';
import { StencilComponent } from '@app/shared/ui/stencil/stencil/stencil';
import { ResearchDataUploadBox, UploadBoxState } from '@app/upload/models/box';
import { UploadBoxService } from '@app/upload/services/upload-box';
// eslint-disable-next-line boundaries/dependencies
import { UploadWorkPackageDialogComponent } from '@app/work-packages/features/upload-work-package-dialog/upload-work-package-dialog';

/**
 * Shows the current user's open Research Data Upload Boxes (RDUBs).
 * For each open box the user can create an upload token (placeholder) or submit the box.
 */
@Component({
  selector: 'app-user-upload-boxes-list',
  imports: [StencilComponent, MatIconModule, MatButtonModule],
  templateUrl: './user-upload-boxes-list.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UserUploadBoxesListComponent {
  #uploadBoxService = inject(UploadBoxService);
  #confirmation = inject(ConfirmationService);
  #dialog = inject(MatDialog);
  #notification = inject(NotificationService);

  protected isLoading = this.#uploadBoxService.boxRetrievalResults.isLoading;
  protected hasError = this.#uploadBoxService.boxRetrievalResults.error;

  /** Open upload boxes */
  protected openBoxes = this.#uploadBoxService.uploadBoxes;

  /** ID of the box currently being submitted, to disable the button while in flight. */
  protected submittingBoxId = signal<string | null>(null);

  constructor() {
    this.#uploadBoxService.loadAllUploadBoxes();
  }
  /**
   * Open the upload token creation dialog for a selected upload box.
   * @param box - the upload box
   */
  createToken(box: ResearchDataUploadBox): void {
    this.#dialog.open(UploadWorkPackageDialogComponent, {
      data: box,
      width: '64rem',
      maxWidth: '96vw',
    });
  }

  /**
   * Ask for confirmation and, on approval, submit the upload box (set state to locked).
   * @param box - the grant whose upload box should be submitted
   */
  submitBox(box: ResearchDataUploadBox): void {
    this.#confirmation.confirm({
      title: 'Submit upload box?',
      message:
        'Submitting closes the upload box. ' +
        'This action can only be reversed by a data steward. ' +
        'Are you sure you want to proceed?',
      confirmText: 'Submit',
      callback: (confirmed) => {
        if (!confirmed) return;
        this.submittingBoxId.set(box.id);
        this.#uploadBoxService
          .updateUploadBox(box.id, {
            version: box.version,
            state: UploadBoxState.locked,
          })
          .subscribe({
            next: () => {
              this.submittingBoxId.set(null);
              this.#notification.showSuccess(
                'The upload box has been submitted successfully.',
              );
            },
            error: () => {
              this.submittingBoxId.set(null);
              this.#notification.showError(
                'Failed to submit the upload box. Please try again.',
              );
            },
          });
      },
    });
  }
}
