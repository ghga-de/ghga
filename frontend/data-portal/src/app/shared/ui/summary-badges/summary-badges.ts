/**
 * A component for displaying collapsible badges in the dataset summaries in the metadata browser
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ChangeDetectionStrategy, Component, input, model } from '@angular/core';
import { MatChipsModule } from '@angular/material/chips';
import { UnderscoreToSpace } from '@app/shared/pipes/underscore-to-space-pipe';

const MAX_ITEMS = 3;

/**
 * A component for badges for dataset summaries
 */
@Component({
  selector: 'app-summary-badges',
  imports: [MatChipsModule, UnderscoreToSpace],
  templateUrl: './summary-badges.html',
  styleUrl: './summary-badges.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SummaryBadgesComponent {
  protected readonly maxItems = MAX_ITEMS;
  readonly data = input.required<
    {
      value: string;
      count: number;
    }[]
  >();

  protected readonly showMore = model(false);

  /**
   * Toggle the show more/less state
   */
  toggleMoreOrLess() {
    this.showMore.set(!this.showMore());
  }
}
