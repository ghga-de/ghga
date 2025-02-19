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
import { RouterLink } from '@angular/router';
import { BaseRouteService } from '@app/shared/services/base-route.service';
import { AccountButtonComponent } from '../account-button/account-button.component';
import { AdminMenuComponent } from '../admin-menu/admin-menu.component';

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
    AdminMenuComponent,
  ],
  styleUrl: './site-header.component.scss',
})
export class SiteHeaderComponent {
  #baseRoute = inject(BaseRouteService);

  route = this.#baseRoute.route;
}
