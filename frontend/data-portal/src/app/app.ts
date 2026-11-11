/**
 * The main app component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import {
  Component,
  EnvironmentInjector,
  OnInit,
  inject,
  runInInjectionContext,
} from '@angular/core';
import { MatIconRegistry } from '@angular/material/icon';
import { RouterOutlet } from '@angular/router';
import { SiteFooter } from '@app/portal/features/site-footer/site-footer';
import { SiteHeader } from '@app/portal/features/site-header/site-header';
import { VersionRibbon } from '@app/portal/features/version-ribbon/version-ribbon';
import { UmamiTracker } from './shared/services/umami';

/**
 * This is the root component of the application.
 */
@Component({
  selector: 'app-root',
  imports: [RouterOutlet, SiteHeader, SiteFooter, VersionRibbon],
  templateUrl: './app.html',
})
export class App implements OnInit {
  #matIconReg = inject(MatIconRegistry);
  #envInjector = inject(EnvironmentInjector);

  /**
   * Run on App component initialization
   */
  ngOnInit(): void {
    this.#initMaterial();
    this.#initUmami();
  }

  /**
   * Set up Material icon ligatures and default font set for the app.
   */
  #initMaterial(): void {
    this.#matIconReg.setDefaultFontSetClass(
      'material-symbols-outlined',
      'mat-ligature-font',
    );
  }

  /**
   * Initialize Umami analytics when the browser is idle.
   */
  #initUmami(): void {
    const scheduleIdle = (cb: () => void) =>
      (window.requestIdleCallback ?? setTimeout)(cb);
    scheduleIdle(() => {
      runInInjectionContext(this.#envInjector, () => inject(UmamiTracker));
    });
  }
}
