/**
 * Show list of IVAs belonging to the current user
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, inject, OnInit } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { ConfirmationService } from '@app/shared/services/confirmation.service';
import { NotificationService } from '@app/shared/services/notification.service';
import { Iva, IvaType } from '@app/verification-addresses/models/iva';
import { IvaTypePipe } from '@app/verification-addresses/pipes/iva-type.pipe';
import { IvaService } from '@app/verification-addresses/services/iva.service';
import { NewIvaDialogComponent } from '../new-iva-dialog/new-iva-dialog.component';
import { VerificationDialogComponent } from '../verification-dialog/verification-dialog.component';

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
  templateUrl: './user-iva-list.component.html',
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
      message:
        'We will send a verification code to the address selected for verification (' +
        address +
        '). Please allow some time for processing' +
        ' your request. When the verification code has been transmitted,' +
        ' you will also be notified via e-mail.',
      callback: (confirmed) => {
        if (confirmed) this.#requestVerification(iva);
      },
      panelClass: 'sm:text-justify',
    });
  }

  /**
   * Submit the verification code for the given IVA
   * @param iva - the IVA to verify
   * @param code - the verification code
   */
  submitVerificationCode(iva: Iva, code: string): void {
    this.#ivaService.validateCodeForIva(iva.id, code).subscribe({
      next: () => {
        this.#notify.showSuccess('Verification was successful');
      },
      error: (err) => {
        switch (err.status) {
          case 403:
            this.#notify.showError(
              'The entered verification code was invalid. Please enter the submitted code correctly.',
            );
            break;
          case 429:
            this.#notify.showError(
              'Too many attempts at entering code. Contact address has been reverted to unverified.',
            );
            break;
          default:
            console.debug(err);
            this.#notify.showError(
              'Code verification currently not possible. Please try again later.',
            );
        }
      },
    });
  }

  /**
   * Ask the user to enter the verification code for the given IVA
   * and then continue with the verification process when the code was entered
   * @param iva - the IVA to verify
   */
  enterVerificationCode(iva: Iva): void {
    const address = this.#ivaAddress(iva);
    const dialogRef = this.#dialog.open(VerificationDialogComponent, {
      data: { address },
    });
    dialogRef.afterClosed().subscribe((code) => {
      if (code) {
        this.submitVerificationCode(iva, code);
      }
    });
  }

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
    dialogRef.afterClosed().subscribe(({ type, value }) => {
      if (type && value) {
        this.add(type, value);
      }
    });
  }
}
