/**
 * Component for data stewards to filter upload boxes.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  model,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { UploadBoxState, UploadBoxStateFilter } from '@app/upload/models/box';
import { UploadBoxService } from '@app/upload/services/upload-box';

/**
 * Upload Box Manager Filter component.
 *
 * This component contains filter controls for the Upload Box Manager.
 */
@Component({
  selector: 'app-upload-box-manager-filter',
  imports: [
    FormsModule,
    MatCardModule,
    MatInputModule,
    MatButtonModule,
    MatSelectModule,
    MatFormFieldModule,
    MatIconModule,
  ],
  templateUrl: './upload-box-manager-filter.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UploadBoxManagerFilterComponent {
  #uploadBoxService = inject(UploadBoxService);

  #filter = this.#uploadBoxService.uploadBoxesFilter;
  showFilter = computed(() => this.#uploadBoxService.uploadBoxes().length > 0);

  displayFilters = signal(false);

  /**
   * The model for upload-box filter properties.
   */
  title = model<string | undefined>(this.#filter().title);
  state = model<UploadBoxStateFilter | undefined>(
    this.#filter().state ?? 'not_archived',
  );
  location = model<string | undefined>(this.#filter().location);

  /**
   * Communicate filter changes to the upload box service.
   */
  #filterEffect = effect(() => {
    this.#uploadBoxService.setUploadBoxesFilter({
      title: this.title(),
      state: this.state(),
      location: this.location(),
    });
  });

  /**
   * All upload-box state filter options, including virtual negation filters.
   */
  stateOptions: { value: UploadBoxStateFilter; label: string }[] = [
    { value: 'not_archived', label: 'Not archived' },
    ...Object.values(UploadBoxState).map((s) => ({
      value: s,
      label: s.charAt(0).toUpperCase() + s.slice(1),
    })),
  ];

  /**
   * All available upload-box locations including display labels.
   */
  locationOptions = this.#uploadBoxService.uploadBoxLocationOptions;
}
