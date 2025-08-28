/**
 * This service manages a global Umami tracker instance.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { inject, Injectable } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { filter } from 'rxjs/operators';
import { ConfigService } from './config.service';

declare global {
  interface Window {
    umami?: {
      track(payload: object): void;
      track(event_name: string, event_data: object): void;
    };
  }
}

/**
 * Umami is a user analytics tool that generates user behavior data that we can monitor in real time in a dashboard.
 * This service creates an instance of the tracker and is injected in the root component of the app.
 */
@Injectable({ providedIn: 'root' })
export class UmamiService {
  #config = inject(ConfigService);
  #router = inject(Router);
  #server_url = this.#config.umami_url;
  #website_id = this.#config.umami_website_id;

  constructor() {
    this.#initializeUmami();
  }

  /**
   * This method initializes the Umami tracker by creating a script tag and adding it to the DOM.
   */
  #initializeUmami() {
    if (!this.#server_url || !this.#website_id) {
      console.warn('Umami is not configured. Skipping initialization.');
      return;
    }
    const script = document.createElement('script');
    script.async = true;
    script.src = this.#server_url;
    script.setAttribute('data-auto-track', 'false');
    script.setAttribute('data-website-id', this.#website_id);
    document.head.appendChild(script);
    this.#trackPageViews();
    this.#trackEvents();
  }

  /**
   * This method tracks navigation events with Umami by subscribing to NavigationEnd events.
   */
  #trackPageViews() {
    this.#router.events
      .pipe(filter((event): event is NavigationEnd => event instanceof NavigationEnd))
      .subscribe((event) => {
        const umami = window.umami;
        if (!umami) return;
        umami.track({
          website: this.#website_id,
          url: event.urlAfterRedirects,
          timestamp: new Date().toISOString(),
          title:
            this.#router.routerState.snapshot.root.firstChild?.routeConfig?.title ||
            document.title,
        });
      });
  }

  /**
   * This method tracks events manually with Umami by subscribing to click events.
   * We need to do this manually since we switched off auto-tracking in the script tag.
   */
  #trackEvents() {
    document.addEventListener('click', (event: MouseEvent) => {
      const umami = window.umami;
      if (!umami) return true;
      const target = (event.target as Element)?.closest('[data-umami-event]');
      if (!target) return true;
      const eventName = target.getAttribute('data-umami-event');
      if (!eventName) return true;
      const eventData: { [key: string]: string } = {};
      for (let attr of target.attributes) {
        if (attr.name.startsWith('data-umami-event-')) {
          const key = attr.name.slice('data-umami-event-'.length);
          eventData[key] = attr.value;
        }
      }
      umami.track(eventName, eventData);
      return true;
    });
  }
}
