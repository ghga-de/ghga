/**
 * A Corner ribbon for showing staging and version info.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { ConfigService } from '@app/shared/services/config';

/**
 * Version ribbon component
 */
@Component({
  selector: 'app-version-ribbon',
  imports: [],
  templateUrl: './version-ribbon.html',
})
export class VersionRibbon implements OnInit {
  #config = inject(ConfigService);
  text = signal(this.#config.ribbonText);

  /**
   * The text split into the version and its build metadata, which a version from a
   * checkout carries (+dev.71.44594f5) and the ribbon shows on a second line
   */
  lines = computed(() => {
    const [main, ...build] = this.text().split('+');
    return { main, build: build.length ? `+${build.join('+')}` : '' };
  });

  /**
   * Always log the Data Portal version when the app is started.
   * This is useful for debugging when the ribbon is deactivated in production.
   */
  ngOnInit(): void {
    const text = this.text() || 'v' + this.#config.version;
    console.info(`Running Data Portal ${text}...`);
  }

  /**
   * Handle click on the ribbon by removing it.
   */
  click(): void {
    this.text.set('');
  }
}
