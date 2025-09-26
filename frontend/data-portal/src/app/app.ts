/**
 * The main app component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, inject, OnInit } from '@angular/core';
import { MatIconRegistry } from '@angular/material/icon';
import { RouterOutlet } from '@angular/router';
import { SiteFooterComponent } from '@app/portal/features/site-footer/site-footer';
import { SiteHeaderComponent } from '@app/portal/features/site-header/site-header';
import { VersionRibbonComponent } from '@app/portal/features/version-ribbon/version-ribbon';
import { UmamiService } from './shared/services/umami';

/**
 * This is the root component of the application.
 */
@Component({
  selector: 'app-root',
  imports: [
    RouterOutlet,
    SiteHeaderComponent,
    SiteFooterComponent,
    VersionRibbonComponent,
  ],
  templateUrl: './app.html',
})
export class AppComponent implements OnInit {
  #matIconReg = inject(MatIconRegistry);
  #umami = inject(UmamiService);

  /**
   * Run on App component initialization
   */
  ngOnInit(): void {
    this.#matIconReg.setDefaultFontSetClass(
      'material-symbols-outlined',
      'mat-ligature-font',
    );
  }
}
