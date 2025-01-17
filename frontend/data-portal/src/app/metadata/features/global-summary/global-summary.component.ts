/**
 * Home page component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, effect, inject } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MetadataService } from '@app/metadata/services/metadata.service';

/**
 * Component for the global summary cards
 */
@Component({
  selector: 'app-global-stats',
  imports: [MatCardModule, MatIconModule],
  templateUrl: './global-summary.component.html',
  styleUrl: './global-summary.component.scss',
})
export class GlobalStatsComponent {
  #metadata = inject(MetadataService);

  #statsError = this.#metadata.globalSummaryError;

  #errorEffect = effect(() => {
    if (this.#statsError()) {
      console.log('Error fetching global summary'); // TODO: show a toast message
    }
  });

  stats = this.#metadata.globalSummary;
}
