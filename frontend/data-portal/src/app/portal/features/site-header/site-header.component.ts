/**
 * Site header component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatNavList } from '@angular/material/list';
import { MatToolbarModule } from '@angular/material/toolbar';
import { NavigationEnd, Router, RouterLink } from '@angular/router';
import { AccountButtonComponent } from '../account-button/account-button.component';

/**
 * This is the site header component
 */
@Component({
  selector: 'app-site-header',
  templateUrl: './site-header.component.html',
  standalone: true,
  imports: [
    MatToolbarModule,
    MatNavList,
    MatButtonModule,
    MatIconModule,
    RouterLink,
    AccountButtonComponent,
  ],
  styleUrl: './site-header.component.scss',
})
export class SiteHeaderComponent {
  #router = inject(Router);

  route: string = '';

  constructor() {
    this.#router.events.subscribe((event) => {
      if (event instanceof NavigationEnd) {
        this.route = this.#router.url;
      } else return;
    });
  }
}
