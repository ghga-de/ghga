/**
 * A Corner ribbon for showing staging and version info.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, inject, OnInit } from '@angular/core';
import { ConfigService } from '@app/shared/services/config.service';

/**
 * Version ribbon component
 */
@Component({
  selector: 'app-version-ribbon',
  imports: [],
  templateUrl: './version-ribbon.component.html',
})
export class VersionRibbonComponent implements OnInit {
  #config = inject(ConfigService);
  text = this.#config.ribbonText;

  /**
   * Always log the Data Portal version when the app is started.
   * This is useful for debugging when the ribbon is deactivated in production.
   */
  ngOnInit(): void {
    const text = this.text || 'v' + this.#config.version;
    console.info(`Running Data Portal ${text}...`);
  }

  /**
   * Handle click on the ribbon by removing it.
   */
  click(): void {
    this.text = '';
  }
}
