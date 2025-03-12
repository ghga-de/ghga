/**
 * The main app component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, inject, OnInit } from '@angular/core';
import { MatIconRegistry } from '@angular/material/icon';
import { RouterOutlet } from '@angular/router';
import { SiteFooterComponent } from '@app/portal/features/site-footer/site-footer.component';
import { SiteHeaderComponent } from '@app/portal/features/site-header/site-header.component';
import { VersionRibbonComponent } from '@app/portal/features/version-ribbon/version-ribbon.component';
import { UmamiService } from './shared/services/umami.service';

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
  templateUrl: './app.component.html',
})
export class AppComponent implements OnInit {
  #matIconReg = inject(MatIconRegistry);
  #umami = inject(UmamiService);

  /**
   * Run on App component initialization
   */
  ngOnInit(): void {
    this.#matIconReg.setDefaultFontSetClass('material-symbols-outlined');
  }
}
