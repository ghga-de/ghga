/**
 * The main app configuration
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { ApplicationConfig, provideZonelessChangeDetection } from '@angular/core';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import {
  provideRouter,
  TitleStrategy,
  withComponentInputBinding,
  withViewTransitions,
} from '@angular/router';
import { provideHttpCache, withHttpCacheInterceptor } from '@ngneat/cashew';

import { DATE_PIPE_DEFAULT_OPTIONS } from '@angular/common';
import { withFetch } from '@angular/common/http';
import { provideDateFnsAdapter } from '@angular/material-date-fns-adapter';
import { MAT_DATE_LOCALE } from '@angular/material/core';
import { csrfInterceptor } from '@app/auth/services/csrf';
import { routes, TemplatePageTitleStrategy } from './app-routes';

import {
  DEFAULT_DATE_FORMATS,
  DEFAULT_DATE_LOCALE,
  DEFAULT_DATE_OUTPUT_FORMAT,
} from '@app/shared/utils/date-formats';

import {
  MAT_PAGINATOR_DEFAULT_OPTIONS,
  MatPaginatorDefaultOptions,
} from '@angular/material/paginator';

const paginatorDefaults: MatPaginatorDefaultOptions = {
  pageSize: 10,
  pageSizeOptions: [10, 25, 50, 100, 250, 500],
};

export const appConfig: ApplicationConfig = {
  providers: [
    provideZonelessChangeDetection(),
    provideRouter(routes, withComponentInputBinding(), withViewTransitions()),
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
    {
      provide: MAT_PAGINATOR_DEFAULT_OPTIONS,
      useValue: paginatorDefaults,
    },
    provideDateFnsAdapter(DEFAULT_DATE_FORMATS),
  ],
};
