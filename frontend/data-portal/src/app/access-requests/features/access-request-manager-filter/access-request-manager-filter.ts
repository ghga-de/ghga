/**
 * Component to filter the list of access requests of all users.
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
import { AccessRequestStatus } from '@app/access-requests/models/access-requests';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { Capitalise } from '@app/shared/pipes/capitalise-pipe';
import { DATE_INPUT_FORMAT_HINT } from '@app/shared/utils/date-formats';

/**
 * Access Request Manager Filter component.
 *
 * This component is used to filter the list of all access requests
 * in the Access Request Manager.
 */
@Component({
  selector: 'app-access-request-manager-filter',
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
  templateUrl: './access-request-manager-filter.html',
})
export class AccessRequestManagerFilterComponent {
  #ars = inject(AccessRequestService);

  #filter = this.#ars.allAccessRequestsFilter;

  readonly dateInputFormatHint = DATE_INPUT_FORMAT_HINT;

  displayFilters = false;

  /**
   * The filter form, starting from the current filter
   */
  protected filterForm = form(
    signal({
      ticketId: this.#filter().ticketId ?? '',
      dataset: this.#filter().dataset ?? '',
      name: this.#filter().requester ?? '',
      dac: this.#filter().dac ?? '',
      fromDate: this.#filter().fromDate ?? (null as Date | null),
      toDate: this.#filter().toDate ?? (null as Date | null),
      status: (this.#filter().status ?? '') as AccessRequestStatus | '',
      requestText: this.#filter().requestText ?? '',
      noteToRequester: this.#filter().noteToRequester ?? '',
      internalNote: this.#filter().internalNote ?? '',
    }),
  );

  /**
   * Communicate filter changes to the access request service
   */
  #filterEffect = effect(() => {
    const filter = this.filterForm().value();
    this.#ars.setAllAccessRequestsFilter({
      ticketId: filter.ticketId || undefined,
      dataset: filter.dataset || undefined,
      requester: filter.name || undefined,
      dac: filter.dac || undefined,
      fromDate: filter.fromDate ?? undefined,
      toDate: filter.toDate ?? undefined,
      status: filter.status || undefined,
      requestText: filter.requestText || undefined,
      noteToRequester: filter.noteToRequester || undefined,
      internalNote: filter.internalNote || undefined,
    });
  });

  /**
   * All access request status values with printable text.
   */
  statusOptions = Object.entries(AccessRequestStatus).map((entry) => ({
    value: entry[0] as keyof typeof AccessRequestStatus,
    text: entry[1],
  }));
}
