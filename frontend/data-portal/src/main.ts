/**
 * The main module
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { isDevMode } from '@angular/core';
import { bootstrapApplication } from '@angular/platform-browser';
import { AppComponent } from './app/app.component';
import { appConfig } from './app/app.config';

/**
 * Start the application
 */
async function startApp() {
  if (isDevMode() && (window.config.mock_api || window.config.mock_oidc)) {
    const { worker } = await import('./mocks/setup');
    await worker.start({ waitUntilReady: true });
  }
}

startApp().then(() =>
  bootstrapApplication(AppComponent, appConfig).catch((err) => console.error(err)),
);
