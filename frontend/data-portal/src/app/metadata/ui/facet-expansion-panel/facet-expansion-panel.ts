/**
 * UI Component for showing a facet, its available and selected options, as well as a search bar
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, computed, input, output, signal } from '@angular/core';
import { form, FormField } from '@angular/forms/signals';
import { MatCheckboxChange, MatCheckboxModule } from '@angular/material/checkbox';
import { MatChipsModule } from '@angular/material/chips';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { Facet } from '@app/metadata/models/search-results';
import { UnderscoreToSpace } from '@app/shared/pipes/underscore-to-space-pipe';
import { highlightMatchingText } from '@app/shared/utils/highlight-matching-text';

const MAX_OPTIONS_BEFORE_FILTERING = 6;

/**
 * Component for the facet expansion panel and options
 */
@Component({
  selector: 'app-facet-expansion-panel',
  imports: [
    MatExpansionModule,
    MatChipsModule,
    MatCheckboxModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    UnderscoreToSpace,
    FormField,
  ],
  templateUrl: './facet-expansion-panel.html',
})
export class FacetExpansionPanelComponent {
  readonly maxOptionsBeforeFiltering = MAX_OPTIONS_BEFORE_FILTERING;

  readonly facet = input.required<Facet>();
  readonly selectedOptions = input.required<string[]>();
  readonly expanded = input.required<boolean>();

  readonly optionRemoved = output<string>();
  readonly optionSelected = output<MatCheckboxChange>();
  readonly panelExpansionChanged = output<boolean>();

  protected filterModel = signal({ filterText: '' });
  protected filterForm = form(this.filterModel);

  protected augmentedOptions = computed(() => {
    const options = this.facet().options;
    const selected = this.selectedOptions();
    const optionsSet = new Set(options.map((option) => option.value));
    const selectedSet = new Set(selected);
    const selectedFiltered = selected
      .filter((option) => !optionsSet.has(option))
      .map((option) => ({ checked: true, value: option, count: 0 }));
    const optionsExtended = options.map((option) => ({
      ...option,
      checked: selectedSet.has(option.value),
    }));
    const allOptions = optionsExtended
      .concat(selectedFiltered)
      .sort((a, b) => a.value.localeCompare(b.value));

    const filter = this.filterModel().filterText.toLocaleLowerCase();

    return allOptions
      .filter((option) => option.value.toLocaleLowerCase().includes(filter))
      .map((option) => ({
        ...option,
        withHighlights: highlightMatchingText(option.value, filter),
      }));
  });

  protected sortedSelectedOptions = computed(() => {
    return this.selectedOptions().sort((a, b) => a.localeCompare(b));
  });
}
