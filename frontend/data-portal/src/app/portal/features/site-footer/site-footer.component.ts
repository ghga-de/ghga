/**
 * Site footer component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, HostBinding } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatRipple } from '@angular/material/core';
import { MatIconModule } from '@angular/material/icon';
import { RouterLink } from '@angular/router';

/**
 * This is the site footer component
 */
@Component({
  selector: 'app-site-footer',
  imports: [RouterLink, MatIconModule, MatButtonModule, MatRipple],
  templateUrl: './site-footer.component.html',
  styleUrl: './site-footer.component.scss',
})
export class SiteFooterComponent {
  year = new Date().getFullYear();
  svg =
    '<svg width="1440" height="120" preserveAspectRatio="none" viewBox="0 0 1440 120" fill="none" xmlns="http://www.w3.org/2000/svg"> <path d="M1482 66.8182H1119.93C854.272 66.8182 592.376 0 364.5 0C136.624 0 -8 66.8182 -8 66.8182V120H1482V66.8182Z" fill="#fff"/></svg>';

  @HostBinding('style.--svg-encoded') background: string =
    'url(data:image/svg+xml;base64,' + btoa(this.svg) + ')';
}
