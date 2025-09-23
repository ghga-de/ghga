/**
 * Home page component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { RouterLink } from '@angular/router';
import { GlobalSummaryComponent } from '@app/metadata/features/global-summary/global-summary.component';
import { ExternalLinkDirective } from '@app/shared/ui/external-link/external-link.directive';

/**
 * This is the home page component
 */
@Component({
  selector: 'app-home-page',
  imports: [MatButtonModule, RouterLink, GlobalSummaryComponent, ExternalLinkDirective],
  templateUrl: './home-page.component.html',
})
export class HomePageComponent {}
