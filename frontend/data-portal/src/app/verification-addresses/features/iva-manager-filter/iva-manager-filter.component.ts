/**
 * Component to filter the list of IVAs of all users.
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
import { DATE_INPUT_FORMAT_HINT } from '@app/shared/utils/date-formats';
import { IvaState } from '@app/verification-addresses/models/iva';
import { IvaStatePipe } from '@app/verification-addresses/pipes/iva-state.pipe';
import { IvaService } from '@app/verification-addresses/services/iva.service';

/**
 * IVA Manager Filter component.
 *
 * This component is used to filter the list of all IVAs
 * in the IVA Manager.
 */
@Component({
  selector: 'app-iva-manager-filter',
  imports: [
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatInputModule,
    MatDatepickerModule,
    MatSelectModule,
    MatFormFieldModule,
    MatIconModule,
  ],
  providers: [IvaStatePipe],
  templateUrl: './iva-manager-filter.component.html',
})
export class IvaManagerFilterComponent {
  #ivaService = inject(IvaService);

  #filter = this.#ivaService.allIvasFilter;

  #ivaStatePipe = inject(IvaStatePipe);

  displayFilters = false;

  readonly dateInputFormatHint = DATE_INPUT_FORMAT_HINT;

  /**
   * The model for the filter properties
   */
  name = model<string>(this.#filter().name);
  fromDate = model<Date | undefined>(this.#filter().fromDate);
  toDate = model<Date | undefined>(this.#filter().toDate);
  state = model<IvaState | undefined>(this.#filter().state);

  /**
   * Communicate filter changes to the IVA service
   */
  #filterEffect = effect(() => {
    this.#ivaService.setAllIvasFilter({
      name: this.name(),
      fromDate: this.fromDate(),
      toDate: this.toDate(),
      state: this.state(),
    });
  });

  /**
   * Get the display name for the IVA state
   * @param state the IVA state in question
   * @returns the display name for the state
   */
  #ivaStateName(state: IvaState): string {
    return this.#ivaStatePipe.transform(state).name;
  }

  /**
   * All IVA status values with printable text.
   */
  stateOptions = Object.entries(IvaState).map((entry) => ({
    value: entry[0] as keyof typeof IvaState,
    text: this.#ivaStateName(entry[1]),
  }));
}
