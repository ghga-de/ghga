/**
 * Home page component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { NgOptimizedImage } from '@angular/common';
import { Component } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { RouterLink } from '@angular/router';
import { GlobalSummaryComponent } from '@app/metadata/features/global-summary/global-summary';
import { ExternalLinkDirective } from '@app/shared/ui/external-link/external-link';

/**
 * This is the home page component
 */
@Component({
  selector: 'app-home-page',
  imports: [
    MatButtonModule,
    RouterLink,
    GlobalSummaryComponent,
    ExternalLinkDirective,
    NgOptimizedImage,
  ],
  templateUrl: './home-page.html',
})
export class HomePageComponent {}
