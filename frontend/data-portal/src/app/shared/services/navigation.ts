/**
 * This service tracks navigation events.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Location } from '@angular/common';
import { inject, Injectable } from '@angular/core';
import { Event, NavigationEnd, Router } from '@angular/router';
import { filter } from 'rxjs/operators';

/**
 * This service has one key function: Calling the platform's back functionality has the downside that it doesn't work if the page was loaded directly (via the URL for example). This service tracks past navigation events. If the page was loaded directly, it will navigate to a fallback route instead of calling the platform's back functionality.
 */
@Injectable({
  providedIn: 'root',
})
export class NavigationTrackingService {
  #navigationCount = 0;
  #location: Location = inject(Location);
  #router: Router = inject(Router);

  constructor() {
    this.#router.events
      .pipe(
        filter(
          (event: Event): event is NavigationEnd => event instanceof NavigationEnd,
        ),
      )
      .subscribe(() => {
        this.#navigationCount++;
      });
  }

  /**
   * Navigates back in the browser history if possible.
   * If there is no prior history within the app session (e.g., the user
   * landed directly on the current page), it navigates to a specified
   * fallback route.
   * @param fallbackRoute An array representing the Angular route to navigate
   * to if no browser history is available
   */
  public back(fallbackRoute?: any[]): void {
    if (this.#navigationCount > 1 || !fallbackRoute) {
      this.#location.back();
    } else {
      this.#router.navigate(fallbackRoute);
    }
  }
}
