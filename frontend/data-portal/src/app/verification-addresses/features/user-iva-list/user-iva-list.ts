/**
 * Show list of IVAs belonging to the current user
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, effect, inject, OnInit, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { ConfirmationService } from '@app/shared/services/confirmation';
import { NotificationService } from '@app/shared/services/notification';
import { Iva, IvaState, IvaType } from '@app/verification-addresses/models/iva';
import { IvaTypePipe } from '@app/verification-addresses/pipes/iva-type-pipe';
import { IvaService } from '@app/verification-addresses/services/iva';
import { NewIvaDialogComponent } from '../new-iva-dialog/new-iva-dialog';
import { VerificationDialogComponent } from '../verification-dialog/verification-dialog';

/**
 * Component to manage the list of IVAs belonging to the current user
 */
@Component({
  selector: 'app-user-iva-list',
  imports: [
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatDialogModule,
    IvaTypePipe,
  ],
  providers: [IvaTypePipe],
  templateUrl: './user-iva-list.html',
})
export class UserIvaListComponent implements OnInit {
  #dialog = inject(MatDialog);
  #confirm = inject(ConfirmationService);
  #notify = inject(NotificationService);
  #ivaService = inject(IvaService);

  #ivas = this.#ivaService.userIvas;
  ivas = this.#ivas.value;
  ivasAreLoading = this.#ivas.isLoading;
  ivasError = this.#ivas.error;

  checkingIvaId = signal<string | null>(null);

  #ivaTypePipe = inject(IvaTypePipe);

  /**
   * Get the type and value of the IVA
   * @param iva the IVA in question
   * @returns the type and value of the IVA combined as address
   */
  #ivaAddress(iva: Iva): string {
    const ivaType = this.#ivaTypePipe.transform(iva.type).name;
    return `${ivaType}: ${iva.value}`;
  }

  /**
   * Load the IVAs of the current user when the component is initialized
   */
  ngOnInit(): void {
    this.#ivaService.loadUserIvas();
  }

  /**
   * Reload the IVAs of the current user
   */
  reload(): void {
    this.#ivaService.reloadUserIvas();
  }

  /**
   * Request verification of the given IVA
   * @param iva - the IVA to be verified
   */
  #requestVerification(iva: Iva): void {
    this.#ivaService.requestCodeForIva(iva.id).subscribe({
      next: () => {
        this.#notify.showSuccess('Verification has been requested');
      },
      error: (err) => {
        console.debug(err);
        this.#notify.showError('Verification request failed');
      },
    });
  }

  /**
   * Request verification of the given IVA after confirmation from user
   * @param iva - the IVA to be verified
   */
  requestVerification(iva: Iva): void {
    const address = this.#ivaAddress(iva);
    this.#confirm.confirm({
      title: 'Request verification of your address',
      message: `We will send a verification code to the address selected for
      verification (${address}). <strong>Please allow some time for processing your
      request.</strong> When the verification code has been transmitted,
      you will also be notified via e-mail.<p
      class="text-error bg-warning/15 mt-3 p-3 font-bold rounded-xl">Note: Verification
      codes via SMS are currently sent out manually by our data stewards, therefore it
      may take up to 2-3 working days until you will receive your code.</p>`,
      callback: (confirmed) => {
        if (confirmed) this.#requestVerification(iva);
      },
      panelClass: 'sm:text-justify',
    });
  }

  /**
   * Enter the verification code if possible at this point.
   * If the IVA is not in the state CodeTransmitted, we first reload the IVAs
   * and check the state again. If it is still not in the state CodeTransmitted,
   * we show a warning that the code has not yet been sent.
   * @param iva - the IVA to verify
   */
  enterVerificationCode(iva: Iva): void {
    if (iva.state === IvaState.CodeTransmitted) {
      const address = this.#ivaAddress(iva);
      this.#dialog.open(VerificationDialogComponent, {
        data: { id: iva.id, address },
      });
    } else {
      if (this.checkingIvaId()) return;
      this.checkingIvaId.set(iva.id);
      this.reload();
    }
  }

  /**
   * Handle manual reloading of the user IVAs
   */
  #ivaReloadEffect = effect(() => {
    const ivas = this.ivas();
    const ivaId = this.checkingIvaId();
    if (ivaId) {
      const iva = ivas.find((iva) => iva.id === ivaId);
      if (iva) {
        const state = iva.state;
        if (state === IvaState.CodeRequested || state === IvaState.CodeCreated) {
          this.#notify.showWarning(
            'A verification code has not yet been sent. Please try again later.',
          );
        } else if (state === IvaState.CodeTransmitted) {
          this.#notify.showSuccess('A verification code has been sent to you.');
          this.enterVerificationCode(iva);
        }
      }
      this.checkingIvaId.set(null);
    }
  });

  /**
   * Delete the given IVA
   * @param iva - the IVA to delete
   */
  #delete(iva: Iva): void {
    this.#ivaService.deleteIva({ ivaId: iva.id }).subscribe({
      next: () => {
        this.#notify.showSuccess('Address has been deleted');
      },
      error: (err) => {
        console.debug(err);
        this.#notify.showError('Address could not be deleted');
      },
    });
  }

  /**
   * Delete the given IVA after confirmation from user
   * @param iva - the IVA to delete
   */
  deleteWhenConfirmed(iva: Iva): void {
    const address = this.#ivaAddress(iva);
    this.#confirm.confirm({
      title: 'Confirm deletion of contact address',
      message:
        `<p>Please confirm deleting the ${address}.` +
        '</p><p><strong>Remember that you will lose access to any datasets' +
        ' whose access was linked to that address</strong>.</p>',
      cancelText: 'Cancel',
      confirmText: 'Confirm deletion',
      callback: (confirmed) => {
        if (confirmed) this.#delete(iva);
      },
    });
  }

  /**
   * Add a new IVA
   * @param type - the type of the IVA to be added
   * @param value - the value of the IVA to be added
   */
  add(type: IvaType, value: string): void {
    this.#ivaService.createIva({ type, value }).subscribe({
      next: () => {
        this.#notify.showSuccess('Contact address has been added');
      },
      error: (err) => {
        console.debug(err);
        this.#notify.showError('Contact address could not be added');
      },
    });
  }

  /**
   * Enter data to create a new IVA
   */
  enterNew(): void {
    const dialogRef = this.#dialog.open(NewIvaDialogComponent);
    dialogRef.afterClosed().subscribe((result) => {
      if (result) {
        const { type, value } = result;
        if (type && value) {
          this.add(type, value);
        }
      }
    });
  }
}
