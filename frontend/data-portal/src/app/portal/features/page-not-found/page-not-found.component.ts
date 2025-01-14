/**
 * PageNotFound component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component } from '@angular/core';
import { MatIcon } from '@angular/material/icon';

/**
 * This is the PageNotFound Component. It gets displayed if the router cannot resolve a route.
 */
@Component({
  selector: 'app-page-not-found',
  imports: [MatIcon],
  templateUrl: './page-not-found.component.html',
})
export class PageNotFoundComponent {}
