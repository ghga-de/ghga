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
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import {
  provideRouter,
  TitleStrategy,
  withComponentInputBinding,
} from '@angular/router';
import { provideHttpCache, withHttpCacheInterceptor } from '@ngneat/cashew';

import { DATE_PIPE_DEFAULT_OPTIONS } from '@angular/common';
import { withFetch } from '@angular/common/http';
import { provideDateFnsAdapter } from '@angular/material-date-fns-adapter';
import { MAT_DATE_LOCALE } from '@angular/material/core';
import { csrfInterceptor } from '@app/auth/services/csrf.service';
import { routes, TemplatePageTitleStrategy } from './app.routes';

import {
  DEFAULT_DATE_FORMATS,
  DEFAULT_DATE_LOCALE,
  DEFAULT_DATE_OUTPUT_FORMAT,
} from '@app/shared/utils/date-formats';

export const appConfig: ApplicationConfig = {
  providers: [
    provideExperimentalZonelessChangeDetection(),
    provideRouter(routes, withComponentInputBinding()),
    { provide: TitleStrategy, useClass: TemplatePageTitleStrategy },
    provideHttpClient(
      withFetch(),
      withInterceptors([withHttpCacheInterceptor(), csrfInterceptor]),
    ),
    // cache all GET requests by default
    provideHttpCache({ strategy: 'implicit' }),
    provideAnimationsAsync(),
    { provide: MAT_DATE_LOCALE, useValue: DEFAULT_DATE_LOCALE },
    {
      provide: DATE_PIPE_DEFAULT_OPTIONS,
      useValue: { dateFormat: DEFAULT_DATE_OUTPUT_FORMAT },
    },
    provideDateFnsAdapter(DEFAULT_DATE_FORMATS),
  ],
};
