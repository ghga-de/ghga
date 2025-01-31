/**
 * Home page component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { RouterLink } from '@angular/router';
import { GlobalSummaryComponent } from '@app/metadata/features/global-summary/global-summary.component';

/**
 * This is the home page component
 */
@Component({
  selector: 'app-home-page',
  imports: [MatIcon, MatButtonModule, RouterLink, GlobalSummaryComponent],
  templateUrl: './home-page.component.html',
  styleUrl: './home-page.component.scss',
})
export class HomePageComponent {}
