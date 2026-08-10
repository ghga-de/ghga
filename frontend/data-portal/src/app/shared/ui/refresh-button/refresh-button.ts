/**
 * A shared button for fetching a list or detail view again.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, computed, input, output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';

/**
 * Button that lets users fetch the data of the surrounding view again.
 *
 * Needed wherever the shown data can change without the portal being involved,
 * for instance while files are uploaded with the GHGA Connector or while other
 * data stewards work on the same objects.
 */
@Component({
  selector: 'app-refresh-button',
  imports: [MatButtonModule, MatIconModule, MatTooltipModule],
  // Keep the button at its natural size when it sits next to a heading that wraps.
  host: { class: 'shrink-0' },
  template: `
    <button
      mat-icon-button
      type="button"
      [disabled]="disabled() || loading()"
      [attr.aria-label]="label()"
      [matTooltip]="label()"
      [attr.data-umami-event]="umamiEvent()"
      (click)="refresh.emit()"
    >
      <mat-icon fontIcon="refresh" [class.animate-spin]="loading()"></mat-icon>
    </button>
  `,
})
export class RefreshButtonComponent {
  /** What is being fetched again, used to build the label, e.g. "the file list". */
  what = input.required<string>();

  /** Whether the data is currently being fetched. */
  loading = input<boolean>(false);

  /** Whether the button is unavailable for reasons other than loading. */
  disabled = input<boolean>(false);

  /** The umami event name to report when the button is used. */
  umamiEvent = input<string | undefined>(undefined);

  /** Emitted when the user asks for the data to be fetched again. */
  refresh = output<void>();

  /** The accessible name and tooltip of the button. */
  protected label = computed<string>(() => `Refresh ${this.what()}`);
}
