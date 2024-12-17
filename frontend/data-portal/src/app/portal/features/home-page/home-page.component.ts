/**
 * Home page component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { RouterLink } from '@angular/router';

/**
 * This is the home page component
 */
@Component({
  selector: 'app-home-page',
  imports: [MatIcon, MatButtonModule, RouterLink],
  templateUrl: './home-page.component.html',
  styleUrl: './home-page.component.scss',
})
export class HomePageComponent {
  // TODO: this is just for testing MSW, remove it later
  #http = inject(HttpClient);
  stats = signal<unknown>({});

  constructor() {
    // TODO: this is just for testing MSW, remove it later
    this.#http.get('api/metldata/stats').subscribe((data) => {
      this.stats.set(JSON.stringify(data));
    });
  }
}
