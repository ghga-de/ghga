/**
 * Component for data stewards to filter the list of access grants.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, effect, inject, signal } from '@angular/core';
import { form, FormField } from '@angular/forms/signals';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { AccessGrantStatus } from '@app/access-requests/models/access-requests';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { Capitalise } from '@app/shared/pipes/capitalise-pipe';

/**
 * Access Grant Manager Filter component.
 *
 * This component is used to filter the list of all access requests
 * in the Access Request Manager.
 */
@Component({
  selector: 'app-access-grant-manager-filter',
  imports: [
    FormField,
    MatCardModule,
    MatInputModule,
    MatButtonModule,
    MatDatepickerModule,
    MatSelectModule,
    MatFormFieldModule,
    MatIconModule,
    Capitalise,
  ],
  templateUrl: './access-grant-manager-filter.html',
})
export class AccessGrantManagerFilterComponent {
  displayFilters = true;
  #ars = inject(AccessRequestService);
  #filter = this.#ars.allAccessGrantsFilter;

  /**
   * The filter form, starting from the current filter
   */
  protected filterForm = form(
    signal({
      user: this.#filter().user ?? '',
      datasetId: this.#filter().dataset_id ?? '',
      status: (this.#filter().status ?? '') as AccessGrantStatus | '',
    }),
  );

  /**
   * Communicate filter changes to the access request service
   */
  #filterEffect = effect(() => {
    const { user, datasetId, status } = this.filterForm().value();
    this.#ars.setAllAccessGrantsFilter({
      dataset_id: datasetId || undefined,
      user: user || undefined,
      status: status || undefined,
    });
  });
}
