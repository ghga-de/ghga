/**
 * Home page component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DecimalPipe } from '@angular/common';
import { Component, computed, effect, inject, Signal } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { FileStats, ValueCount } from '@app/metadata/models/global-summary';
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
    DecimalPipe,
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
  files: Signal<FileStats> = computed(() => this.#getFiles());

  /**
   * Aggregates file statistics from the individual file stats in the global summary.
   * @returns The aggregated file statistics from all file stats.
   */
  #getFiles(): FileStats {
    let totalCount = 0;
    const totalFormats: Map<string, number> = new Map();
    Object.entries(this.stats())
      .filter(([key]) => key.endsWith('File'))
      .forEach(([, value]) => {
        const fileStats = value as FileStats;
        totalCount += fileStats.count;
        const format = fileStats.stats?.format || [];
        format.forEach(({ value, count }) =>
          totalFormats.set(value, (totalFormats.get(value) || 0) + count),
        );
      });
    const format: ValueCount[] = Array.from(totalFormats.entries()).map(
      ([value, count]) => ({ value, count }),
    );
    return {
      count: totalCount,
      stats: format ? { format } : undefined,
    };
  }
}
