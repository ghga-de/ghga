/**
 * Component for rendering a shortened text with a button to copy the full text
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ClipboardModule } from '@angular/cdk/clipboard';
import { Component, inject, input } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { NotificationService } from '@app/shared/services/notification';

/**
 * Component for rendering a shortened text with a button to copy the full text
 */
@Component({
  selector: 'app-with-copy-button',
  imports: [MatButtonModule, MatIconModule, ClipboardModule],
  templateUrl: './with-copy-button.html',
})
export class WithCopyButton {
  value = input.required<string>();
  notifyMessage = input<string>('The full text has been copied to clipboard');

  #notify = inject(NotificationService);

  /**
   * Notify user after full text was copied to clipboard
   */
  notifyCopied() {
    this.#notify.showInfo(this.notifyMessage(), 1000);
  }
}
