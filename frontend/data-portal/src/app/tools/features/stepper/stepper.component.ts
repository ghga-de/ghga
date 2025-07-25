/**
 * This component shows a stepper
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { CommonModule } from '@angular/common';
import { Component, input } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { StepDetails } from '@app/tools/models/stepper';

/**
 * This component displays a stepper, in which each step can have one of the following states:
 * - idle: The step is not started yet.
 * - ongoing: The step is currently being processed.
 * - succeeded: The step has been successfully completed.
 * - failed: The step has failed.
 */
@Component({
  selector: 'app-stepper',
  templateUrl: './stepper.component.html',
  styleUrls: ['./stepper.component.scss'],
  imports: [CommonModule, MatButtonModule, MatIconModule],
})
export class StepperComponent {
  steps = input.required<StepDetails[]>();
}
