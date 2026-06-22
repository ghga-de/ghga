/**
 * PageNotFound component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component } from '@angular/core';
import { MatIcon } from '@angular/material/icon';
import { ExternalLinkDirective } from '@app/shared/ui/external-link/external-link';

/**
 * This is the PageNotFound Component. It gets displayed if the router cannot resolve a route.
 */
@Component({
  selector: 'app-page-not-found',
  imports: [MatIcon, ExternalLinkDirective],
  templateUrl: './page-not-found.html',
})
export class PageNotFoundComponent {}
