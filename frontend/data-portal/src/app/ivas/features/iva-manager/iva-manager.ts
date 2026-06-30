/**
 * Component that hosts the IVA Manager feature.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, inject, OnInit } from '@angular/core';
import { IvaService } from '@app/ivas/services/iva';
import { IvaManagerFilterComponent } from '../iva-manager-filter/iva-manager-filter';
import { IvaManagerListComponent } from '../iva-manager-list/iva-manager-list';

/**
 * IVA Manager component.
 *
 * The IVA Manager allows data stewards to manage the IVAs of all users,
 * particularly it helps sending out verification codes to users.
 */
@Component({
  selector: 'app-iva-manager',
  imports: [IvaManagerListComponent, IvaManagerFilterComponent],
  templateUrl: './iva-manager.html',
})
export class IvaManagerComponent implements OnInit {
  #ivaService = inject(IvaService);

  /**
   * Load the IVAs when the component is initialized
   */
  ngOnInit(): void {
    this.#ivaService.loadAllIvas();
  }
}
