/**
 * A component that can show a stencil while data is loading.
 * @copyright The GHGA Authors and Wilson Mendes
 * @license Apache-2.0
 * This has been inspired by https://github.com/willmendesneto/ngx-skeleton-loader.
 */

// eslint-disable-next-line header/header
import { Component, computed, input } from '@angular/core';

const DEFAULT_COUNT = 1;
const DEFAULT_TEXT = 'Loading...';
const DEFAULT_LABEL = 'loading';
const DEFAULT_PULSE = true;

/**
 * Provides a stencil UI element.
 *
 * It can be used to display a loading state before the actual content is available.
 * The component can be configured with a few option.
 */
@Component({
  selector: 'app-stencil',
  imports: [],
  templateUrl: './stencil.component.html',
  styleUrl: './stencil.component.scss',
})
export class StencilComponent {
  count = input<number>(DEFAULT_COUNT);
  text = input<string>(DEFAULT_TEXT);
  label = input<string>(DEFAULT_LABEL);
  pulse = input<boolean>(DEFAULT_PULSE);

  items = computed(() => [...Array(this.count())].map((_, index) => index));
}
