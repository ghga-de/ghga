/**
 * This service manages a global Umami tracker instance.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { inject, Injectable } from '@angular/core';
import { ConfigService } from './config.service';

/**
 * Umami is a user analytics tool that generates user behavior data that we can monitor in real time in a dashboard.
 * This service creates an instance of the tracker and is injected in the root component of the app.
 */
@Injectable({
  providedIn: 'root',
})
export class UmamiService {
  #config = inject(ConfigService);
  #server_url = this.#config.umami_url;
  #website_id = this.#config.umami_website_id;

  constructor() {
    this.#initializeUmami();
  }

  /**
   * This method initializes the Umami tracker by creating a script tag and adding it to the DOM.
   */
  #initializeUmami() {
    const script = document.createElement('script');
    script.src = this.#server_url;
    script.setAttribute('data-website-id', this.#website_id);
    document.head.appendChild(script);
  }
}
