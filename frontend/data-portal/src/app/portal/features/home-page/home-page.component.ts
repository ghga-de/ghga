import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';

/**
 * This is the home page component
 */
@Component({
  selector: 'app-home-page',
  imports: [],
  templateUrl: './home-page.component.html',
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
