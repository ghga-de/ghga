/**
 * Short module description
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, computed, input } from '@angular/core';
import { SchemapackOutputStatus } from '@app/tools/models/status-text';

/**
 * This component shows the status text box for the Schemapack validation tool.
 */
@Component({
  selector: 'app-status-text-box',
  imports: [],
  templateUrl: './status-text-box.component.html',
})
export class StatusTextBoxComponent {
  status = input.required<SchemapackOutputStatus>();
  statusText = input.required<string>();
  isError = computed(() => this.status() === SchemapackOutputStatus.ERROR);
  isReady = computed(() => this.status() === SchemapackOutputStatus.READY);
  isLoading = computed(() => this.status() === SchemapackOutputStatus.LOADING);
  isSuccess = computed(() => this.status() === SchemapackOutputStatus.SUCCESS);
}
