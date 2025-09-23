/**
 * Menu component for all data steward management pages
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, computed, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { RouterLink } from '@angular/router';
import { BaseRouteService } from '@app/shared/services/base-route.service';

/**
 * Component that shows an admin menu button with the sub menu items for data stewards
 */
@Component({
  selector: 'app-admin-menu',
  imports: [MatIconModule, MatButtonModule, MatMenuModule, RouterLink],
  templateUrl: './admin-menu.component.html',
})
export class AdminMenuComponent {
  #baseRoute = inject(BaseRouteService);
  #route = this.#baseRoute.route;
  isUserManagerRoute = computed<boolean>(() =>
    this.#route().startsWith('user-manager'),
  );
  isIvaManagerRoute = computed<boolean>(() => this.#route().startsWith('iva-manager'));
  isAccessGrantManagerRoute = computed<boolean>(() =>
    this.#route().startsWith('access-grant-manager'),
  );
  isAccessRequestsManagerRoute = computed<boolean>(() =>
    this.#route().startsWith('access-request-manager'),
  );
  isAdminRoute = computed<boolean>(
    () =>
      this.isUserManagerRoute() ||
      this.isIvaManagerRoute() ||
      this.isAccessRequestsManagerRoute() ||
      this.isAccessGrantManagerRoute() ||
      this.isAccessRequestsManagerRoute(),
  );
}
