/**
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, inject, OnInit } from '@angular/core';
import { MatIconRegistry } from '@angular/material/icon';
import { RouterOutlet } from '@angular/router';
import { ShowSessionComponent } from '@app/portal/features/show-session/show-session.component';
import { SiteFooterComponent } from '@app/portal/features/site-footer/site-footer.component';
import { SiteHeaderComponent } from '@app/portal/features/site-header/site-header.component';

/**
 * This is the root component of the application.
 */
@Component({
  selector: 'app-root',
  imports: [
    RouterOutlet,
    SiteHeaderComponent,
    SiteFooterComponent,
    ShowSessionComponent,
  ],
  templateUrl: './app.component.html',
})
export class AppComponent implements OnInit {
  #matIconReg = inject(MatIconRegistry);

  /**
   * Run on App component initialization
   */
  ngOnInit(): void {
    this.#matIconReg.setDefaultFontSetClass('material-symbols-outlined');
  }
}
