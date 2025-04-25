/**
 * Component for generating paragraphs by splitting lines of text
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, computed, input } from '@angular/core';
import { SplitLinesPipe } from '@app/shared/pipes/split-lines.pipe';

/**
 * Component for generating paragraphs by splitting lines of text
 */
@Component({
  selector: 'app-paragraphs',
  imports: [SplitLinesPipe],
  templateUrl: './paragraphs.component.html',
})
export class ParagraphsComponent {
  text = input.required<string>();
  label = input<string>();
  labelWithColon = computed(() => (this.label() ? `${this.label()}: ` : undefined));
  pClasses = input<string>();
}
