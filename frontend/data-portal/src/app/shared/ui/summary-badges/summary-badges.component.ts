/**
 * A component for displaying collapsible badges in the dataset summaries in the metadata browser
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, input } from '@angular/core';
import { MatChipsModule } from '@angular/material/chips';
import { UnderscoreToSpace } from '@app/shared/utils/underscore-to-space.pipe';

/**
 * A component for badges for dataset summaries
 */
@Component({
  selector: 'app-summary-badges',
  imports: [MatChipsModule, UnderscoreToSpace],
  templateUrl: './summary-badges.component.html',
  styleUrl: './summary-badges.component.scss',
})
export class SummaryBadgesComponent {
  data = input.required<
    {
      value: string;
      count: number;
    }[]
  >();
}
