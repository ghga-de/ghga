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
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import {
  IvaStatePrintable,
  IvaType,
  IvaTypePrintable,
  UserWithIva,
} from '@app/verification-addresses/models/iva';
import { IvaService } from '@app/verification-addresses/services/iva.service';

const IVA_TYPE_ICONS: { [K in keyof typeof IvaType]: string } = {
  Phone: 'smartphone',
  Fax: 'fax',
  PostalAddress: 'local_post_office',
  InPerson: 'handshakes',
};

/**
 * IVA Manager List component.
 *
 * This component lists all the IVAs of all users in the IVA Manager.
 * Filter conditions can be applied to the list.
 */
@Component({
  selector: 'app-iva-manager-list',
  imports: [
    MatTableModule,
    MatButtonModule,
    MatIconModule,
    MatSortModule,
    MatPaginatorModule,
  ],
  templateUrl: './iva-manager-list.component.html',
  styleUrl: './iva-manager-list.component.scss',
})
export class IvaManagerListComponent implements AfterViewInit {
  #ivaService = inject(IvaService);

  ivas = this.#ivaService.allIvas;
  ivasAreLoading = this.#ivaService.allIvasAreLoading;
  ivasError = this.#ivaService.allIvasError;

  source = new MatTableDataSource<UserWithIva>([]);

  defaultTablePageSize = 10;
  tablePageSizeOptions = [5, 10, 25, 50, 100, 250, 500];

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
   * Get the type name of an IVA
   * @param iva - the IVA in question
   * @returns the printable type name
   */
  typeName(iva: UserWithIva): string {
    return IvaTypePrintable[iva.type];
  }

  /**
   * Get a suitable icon for an IVA
   * @param iva - the IVA in question
   * @returns the icon corresponding to the type
   */
  typeIconName(iva: UserWithIva): string {
    return IVA_TYPE_ICONS[iva.type];
  }

  /**
   * Get the status name of an IVA
   * @param iva - the IVA in question
   * @returns the printable status name
   */
  statusName(iva: UserWithIva): string {
    return IvaStatePrintable[iva.state];
  }
}
