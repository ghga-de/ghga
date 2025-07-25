/**
 * Menu component for all tool pages
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
 * Component that shows an tools menu button with the sub menu items for the tools we offer
 */
@Component({
  selector: 'app-tools-menu',
  imports: [MatIconModule, MatButtonModule, MatMenuModule, RouterLink],
  templateUrl: './tools-menu.component.html',
  styleUrl: './tools-menu.component.scss',
})
export class ToolsMenuComponent {
  #baseRoute = inject(BaseRouteService);
  #route = this.#baseRoute.route;
  isPlaygroundRoute = computed<boolean>(
    () => this.#route() === 'schemapack-playground',
  );
  isMetadataRoute = computed<boolean>(() => this.#route() === 'metadata-validator');
  isToolsRoute = computed<boolean>(
    () => this.isMetadataRoute() || this.isPlaygroundRoute(),
  );
}
