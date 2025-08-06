/**
 * Component to filter the list of access requests of all users.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, effect, inject, model } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { AccessRequestStatus } from '@app/access-requests/models/access-requests';
import { AccessRequestService } from '@app/access-requests/services/access-request.service';
import { Capitalise } from '@app/shared/pipes/capitalise.pipe';
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
    FormsModule,
    MatCardModule,
    MatInputModule,
    MatButtonModule,
    MatDatepickerModule,
    MatSelectModule,
    MatFormFieldModule,
    MatIconModule,
    Capitalise,
  ],
  templateUrl: './access-request-manager-filter.component.html',
  styleUrl: './access-request-manager-filter.component.scss',
})
export class AccessRequestManagerFilterComponent {
  #ars = inject(AccessRequestService);

  #filter = this.#ars.allAccessRequestsFilter;

  readonly dateInputFormatHint = DATE_INPUT_FORMAT_HINT;

  displayFilters = false;

  /**
   * The model for the filter properties
   */
  ticketId = model<string | undefined>(this.#filter().ticketId);
  dataset = model<string | undefined>(this.#filter().dataset);
  name = model<string | undefined>(this.#filter().requester);
  dac = model<string | undefined>(this.#filter().dac);
  fromDate = model<Date | undefined>(this.#filter().fromDate);
  toDate = model<Date | undefined>(this.#filter().toDate);
  status = model<AccessRequestStatus | undefined>(this.#filter().status);
  requestText = model<string | undefined>(this.#filter().requestText);
  noteToRequester = model<string | undefined>(this.#filter().noteToRequester);
  internalNote = model<string | undefined>(this.#filter().internalNote);

  /**
   * Communicate filter changes to the access request service
   */
  #filterEffect = effect(() => {
    this.#ars.setAllAccessRequestsFilter({
      ticketId: this.ticketId(),
      dataset: this.dataset(),
      requester: this.name(),
      dac: this.dac(),
      fromDate: this.fromDate(),
      toDate: this.toDate(),
      status: this.status(),
      requestText: this.requestText(),
      noteToRequester: this.noteToRequester(),
      internalNote: this.internalNote(),
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
