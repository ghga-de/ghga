/**
 * The main app configuration
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { provideHttpClient, withInterceptors } from '@angular/common/http';
import {
  ApplicationConfig,
  provideExperimentalZonelessChangeDetection,
} from '@angular/core';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideRouter, TitleStrategy } from '@angular/router';
import { provideHttpCache, withHttpCacheInterceptor } from '@ngneat/cashew';

import { withFetch } from '@angular/common/http';
import { csrfInterceptor } from '@app/auth/services/csrf.service';
import { routes, TemplatePageTitleStrategy } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideExperimentalZonelessChangeDetection(),
    provideRouter(routes),
    { provide: TitleStrategy, useClass: TemplatePageTitleStrategy },
    provideHttpClient(
      withFetch(),
      withInterceptors([withHttpCacheInterceptor(), csrfInterceptor]),
    ),
    // cache all GET requests by default
    provideHttpCache({ strategy: 'implicit' }),
    provideNoopAnimations(),
    provideAnimationsAsync(),
  ],
};
