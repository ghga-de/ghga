/**
 * Site header component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, inject, ViewChild } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatRippleModule } from '@angular/material/core';
import { MatIconModule } from '@angular/material/icon';
import { MatNavList } from '@angular/material/list';
import { MatSidenav, MatSidenavModule } from '@angular/material/sidenav';
import { MatToolbarModule } from '@angular/material/toolbar';
import { NavigationStart, Router, RouterLink } from '@angular/router';
import { AccountButtonComponent } from '../account-button/account-button';
import { SiteHeaderNavButtonsComponent } from '../site-header-nav-buttons/site-header-nav-buttons';

/**
 * This is the site header component
 */
@Component({
  selector: 'app-site-header',
  templateUrl: './site-header.html',
  imports: [
    MatToolbarModule,
    MatNavList,
    MatButtonModule,
    MatIconModule,
    RouterLink,
    AccountButtonComponent,
    MatSidenavModule,
    SiteHeaderNavButtonsComponent,
    MatRippleModule,
  ],
  styleUrl: './site-header.scss',
})
export class SiteHeaderComponent {
  #router = inject(Router);
  @ViewChild('sidenav') sidenav: MatSidenav | undefined;

  constructor() {
    this.#router.events.subscribe((event) => {
      if (event instanceof NavigationStart) {
        this.sidenav?.close();
      }
    });
  }
}
