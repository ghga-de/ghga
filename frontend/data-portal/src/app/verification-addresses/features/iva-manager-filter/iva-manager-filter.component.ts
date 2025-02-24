/**
 * Component to filter the list of IVAs of all users.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, effect, inject, model } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { IvaState, IvaStatePrintable } from '@app/verification-addresses/models/iva';
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
    MatInputModule,
    MatDatepickerModule,
    MatSelectModule,
    MatFormFieldModule,
    MatIconModule,
  ],
  templateUrl: './iva-manager-filter.component.html',
  styleUrl: './iva-manager-filter.component.scss',
})
export class IvaManagerFilterComponent {
  #ivaService = inject(IvaService);

  #filter = this.#ivaService.allIvasFilter;

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
   * All IVA status values with printable text.
   */
  stateOptions = Object.entries(IvaStatePrintable).map((entry) => ({
    value: entry[0] as keyof typeof IvaState,
    text: entry[1],
  }));
}
