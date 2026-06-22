/**
 * Nav buttons for the header navigation, both the sidenav and the top nav
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, computed, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { RouterLink } from '@angular/router';
import { AuthService } from '@app/auth/services/auth';
import { BaseRouteService } from '@app/shared/services/base-route';
import { ExternalLinkDirective } from '@app/shared/ui/external-link/external-link';
import { AdminMenuComponent } from '../admin-menu/admin-menu';

/**
 * Component for the navigation button components
 */
@Component({
  selector: 'app-site-header-nav-buttons',
  imports: [
    MatIconModule,
    MatButtonModule,
    RouterLink,
    AdminMenuComponent,
    MatMenuModule,
    ExternalLinkDirective,
  ],
  templateUrl: './site-header-nav-buttons.html',
})
export class SiteHeaderNavButtonsComponent {
  #baseRoute = inject(BaseRouteService);
  #route = this.#baseRoute.route;
  #auth = inject(AuthService);

  /**
   * Whether the user is a data steward
   */
  protected isDataSteward = computed(() => this.#auth.roles().includes('data_steward'));

  /**
   * Whether the "Home" navigation button should be highlighted as being active
   */
  protected homeActive = computed(() => this.#route() === '');

  /**
   * Whether the "Browse" navigation button should be highlighted as being active
   */
  protected browseActive = computed(() =>
    ['browse', 'dataset'].some((prefix) => this.#route().startsWith(prefix)),
  );
}
