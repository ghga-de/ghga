/**
 * Simple service that provides the current base route
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { inject, Injectable, signal } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';

/**
 * A simple service that provides the current base route
 */
@Injectable({ providedIn: 'root' })
export class BaseRouteService {
  #router = inject(Router);

  /**
   * A signal that gets the first part of the current route
   */
  route = signal<string>('');

  constructor() {
    this.#router.events.subscribe((event) => {
      if (event instanceof NavigationEnd) {
        this.route.set(this.#router.url.split(/[//?]/g).filter((p) => p)[0] || '');
      }
    });
  }
}
