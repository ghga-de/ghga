/**
 * Home page component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, computed, effect, inject } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MetadataStatsService } from '@app/metadata/services/metadata-stats.service';
import { UnderscoreToSpace } from '@app/shared/pipes/underscore-to-space.pipe';
import { NotificationService } from '@app/shared/services/notification.service';
import { StencilComponent } from '@app/shared/ui/stencil/stencil/stencil.component';

/**
 * Component for the global summary cards
 */
@Component({
  selector: 'app-global-stats',
  imports: [
    MatCardModule,
    MatIconModule,
    UnderscoreToSpace,
    MatProgressSpinnerModule,
    StencilComponent,
  ],
  templateUrl: './global-summary.component.html',
  styleUrl: './global-summary.component.scss',
  providers: [MetadataStatsService],
})
export class GlobalSummaryComponent {
  #notify = inject(NotificationService);
  #metadata = inject(MetadataStatsService);

  #stats = this.#metadata.globalSummary;

  #errorEffect = effect(() => {
    if (this.#stats.error()) {
      this.#notify.showWarning('Error fetching statistics');
    }
  });

  stats = computed(() => this.#stats.value());
  isLoading = computed(() => this.#stats.isLoading());

  datasets = computed(() => this.stats().Dataset);
  methods = computed(() => this.stats().ExperimentMethod);
  individuals = computed(() => this.stats().Individual);
  files = computed(() => this.stats().ProcessDataFile);
}
