/**
 * Component that lists all the IVAs.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import {
  AfterViewInit,
  Component,
  effect,
  inject,
  QueryList,
  ViewChild,
  ViewChildren,
} from '@angular/core';

import { DatePipe } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { ConfirmationService } from '@app/shared/services/confirmation.service';
import { NotificationService } from '@app/shared/services/notification.service';
import { UserWithIva } from '@app/verification-addresses/models/iva';
import { IvaStatePipe } from '@app/verification-addresses/pipes/iva-state.pipe';
import { IvaTypePipe } from '@app/verification-addresses/pipes/iva-type.pipe';
import { IvaService } from '@app/verification-addresses/services/iva.service';
import { CodeCreationDialogComponent } from '../code-creation-dialog/code-creation-dialog.component';

/**
 * IVA Manager List component.
 *
 * This component lists all the IVAs of all users in the IVA Manager.
 * Filter conditions can be applied to the list.
 */
@Component({
  selector: 'app-iva-manager-list',
  imports: [
    DatePipe,
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatSortModule,
    MatPaginatorModule,
    IvaTypePipe,
    IvaStatePipe,
  ],
  providers: [IvaTypePipe],
  templateUrl: './iva-manager-list.component.html',
  styleUrl: './iva-manager-list.component.scss',
})
export class IvaManagerListComponent implements AfterViewInit {
  #dialog = inject(MatDialog);
  #confirmationService = inject(ConfirmationService);
  #notificationService = inject(NotificationService);
  #ivaService = inject(IvaService);
  #ivaTypePipe = inject(IvaTypePipe);

  #ivas = this.#ivaService.allIvas;
  ivas = this.#ivaService.allIvasFiltered;
  ivasAreLoading = this.#ivas.isLoading;
  ivasError = this.#ivas.error;

  source = new MatTableDataSource<UserWithIva>([]);

  defaultTablePageSize = 10;
  tablePageSizeOptions = [10, 25, 50, 100, 250, 500];

  #updateSourceEffect = effect(() => (this.source.data = this.ivas()));

  #ivaSortingAccessor = (iva: UserWithIva, key: string) => {
    switch (key) {
      case 'user':
        const parts = iva.user_name.split(' ');
        return parts.reverse().join(',');
      default:
        const value = iva[key as keyof UserWithIva];
        if (typeof value === 'string' || typeof value === 'number') {
          return value;
        }
        return '';
    }
  };

  @ViewChildren(MatSort) matSorts!: QueryList<MatSort>;
  @ViewChildren(MatPaginator) matPaginators!: QueryList<MatPaginator>;
  @ViewChild('paginator') paginator!: MatPaginator;
  @ViewChild('sort') sort!: MatSort;

  /**
   * Assign sorting
   */
  #addSorting() {
    if (this.sort) this.source.sort = this.sort;
  }

  /**
   * Assign pagination
   */
  #addPagination() {
    if (this.paginator) this.source.paginator = this.paginator;
  }

  /**
   * Get the display name for the IVA type
   * @param iva the IVA in question
   * @returns the display name for the type
   */
  #ivaTypeName(iva: UserWithIva): string {
    return this.#ivaTypePipe.transform(iva.type).name;
  }

  /**
   * After the view has been initialised
   * assign the sorting of the table to the data source
   */
  ngAfterViewInit() {
    this.source.sortingDataAccessor = this.#ivaSortingAccessor;
    this.#addSorting();
    this.#addPagination();
    this.matSorts.changes.subscribe(() => this.#addSorting());
    this.matPaginators.changes.subscribe(() => this.#addPagination());
  }

  /**
   * Invalidate the given IVA
   * @param iva - the IVA to be invalidated
   */
  #invalidate(iva: UserWithIva): void {
    this.#ivaService.unverifyIva(iva.id).subscribe({
      next: () => this.#notificationService.showSuccess('IVA has been invalidated'),
      error: (err) => {
        console.debug(err);
        this.#notificationService.showError('IVA could not be invalidated');
      },
    });
  }

  /**
   * Invalidate an IVA after confirmation
   * @param iva - the IVA to invalidate
   */
  invalidateWhenConfirmed(iva: UserWithIva) {
    const ivaType = this.#ivaTypeName(iva);
    this.#confirmationService.confirm({
      title: 'Confirm invalidation of IVA',
      message:
        `Do you really wish to invalidate the ${ivaType} IVA of` +
        ` ${iva.user_name} with address "${iva.value}"?` +
        ' The user will lose access to any dataset linked to this IVA.',
      cancelText: 'Cancel',
      confirmText: 'Confirm invalidation',
      callback: (confirmed) => {
        if (confirmed) this.#invalidate(iva);
      },
    });
  }

  /**
   * Mark verification code as transmitted
   * @param iva - the IVA for which the code was transmitted
   */
  #markAsTransmitted(iva: UserWithIva): void {
    this.#ivaService.confirmTransmissionForIva(iva.id).subscribe({
      next: () => {
        this.#notificationService.showSuccess(
          'Transmission of verification code confirmed',
        );
      },
      error: (err) => {
        console.debug(err);
        this.#notificationService.showError(
          'Transmission of verification code could not be confirmed',
        );
      },
    });
  }

  /**
   * Mark verification code as transmitted after confirmation
   * @param iva - the IVA for which the code was transmitted
   */
  markAsTransmittedWhenConfirmed(iva: UserWithIva) {
    const ivaType = this.#ivaTypeName(iva);
    this.#confirmationService.confirm({
      title: 'Confirm code transmission',
      message:
        'Please confirm the transmission of the verification code' +
        ` the ${ivaType} IVA of ${iva.user_name} with address "${iva.value}".`,
      cancelText: 'Cancel',
      confirmText: 'Confirm transmission',
      callback: (confirmed) => {
        if (confirmed) this.#markAsTransmitted(iva);
      },
    });
  }

  /**
   * (Re)create a verification code
   * @param iva - the IVA for which the code should be created
   */
  createCode(iva: UserWithIva) {
    this.#ivaService.createCodeForIva(iva.id).subscribe({
      next: (code) => {
        this.#notificationService.showSuccess('Verification code has been created');
        const dialogRef = this.#dialog.open(CodeCreationDialogComponent, {
          data: { ...iva, code },
        });
        dialogRef.afterClosed().subscribe((doConfirm) => {
          if (doConfirm) {
            this.#markAsTransmitted(iva);
          }
        });
      },
      error: (err) => {
        console.debug(err);
        this.#notificationService.showError('Verification code could not be created');
      },
    });
  }
}
