/**
 * A Corner ribbon for showing staging and version info.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, inject } from '@angular/core';
import { ConfigService } from '@app/shared/services/config.service';

/**
 * Version ribbon component
 */
@Component({
  selector: 'app-version-ribbon',
  imports: [],
  templateUrl: './version-ribbon.component.html',
  styleUrl: './version-ribbon.component.scss',
})
export class VersionRibbonComponent {
  #config = inject(ConfigService);
  text = this.#config.ribbonText;

  /**
   * Handle click on the ribbon by removing it.
   */
  click(): void {
    this.text = '';
  }
}
