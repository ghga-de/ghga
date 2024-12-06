/**
 * The main module
 */

import { isDevMode } from '@angular/core';
import { bootstrapApplication } from '@angular/platform-browser';
import { AppComponent } from './app/app.component';
import { appConfig } from './app/app.config';

/**
 * Start the application
 */
async function startApp() {
  if (isDevMode()) {
    const { worker } = await import('./mocks/setup');
    await worker.start({ waitUntilReady: true });
  }
}

startApp().then(() =>
  bootstrapApplication(AppComponent, appConfig).catch((err) => console.error(err)),
);
