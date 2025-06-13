/**
 * This Component is the content of a dialog used to request access to a dataset
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, computed, inject, input, model, signal } from '@angular/core';
import {
  AbstractControl,
  FormControl,
  FormsModule,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import {
  MatDatepickerInputEvent,
  MatDatepickerModule,
} from '@angular/material/datepicker';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatFormField, MatHint, MatLabel } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { AccessRequestDialogData } from '@app/access-requests/models/access-requests';
import { ConfigService } from '@app/shared/services/config.service';
import { DATE_INPUT_FORMAT_HINT } from '@app/shared/utils/date-formats';

/**
 * This component contains a form for all the data needed for an access request.
 */
@Component({
  selector: 'app-access-request-dialog',
  imports: [
    MatDatepickerModule,
    MatHint,
    MatLabel,
    MatFormField,
    MatInputModule,
    FormsModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
  ],
  templateUrl: './access-request-dialog.component.html',
})
export class AccessRequestDialogComponent {
  readonly dialogRef = inject(MatDialogRef<AccessRequestDialogComponent>);
  readonly data = inject<AccessRequestDialogData>(MAT_DIALOG_DATA);
  #config = inject(ConfigService);
  readonly dateInputFormatHint = DATE_INPUT_FORMAT_HINT;
  readonly emailFormControl = new FormControl(this.data.email, [
    Validators.required,
    Validators.email,
  ]);
  readonly descriptionFormControl = new FormControl(this.data.description, [
    Validators.required,
  ]);
  fromDate = model(this.data.fromDate);
  untilDate = model(this.data.untilDate);
  todayMidnight = new Date();
  minFromDate = new Date();
  minUntilDate = new Date();
  maxFromDate = new Date();
  maxUntilDate = new Date();
  datasetID = input.required<string>();
  descriptionErrorMessage = signal('');
  emailErrorMessage = signal('');
  untilDateErrorMessage = signal('');
  fromDateErrorMessage = signal('');
  submitDisabled = computed(() => {
    return this.emailErrorMessage().length ||
      this.fromDateErrorMessage().length ||
      this.untilDateErrorMessage().length ||
      this.descriptionErrorMessage().length
      ? true
      : false;
  });

  constructor() {
    this.todayMidnight.setHours(0, 0, 0, 0);
    this.fromDate.set(new Date(this.todayMidnight));

    let d = new Date(this.todayMidnight);
    d.setHours(23, 59, 59, 999);
    this.minUntilDate.setDate(d.getDate() + this.#config.accessGrantMinDays);

    d.setDate(d.getDate() + this.#config.defaultAccessDurationDays);
    this.untilDate.set(d);

    this.updateUntilRangeForFromValue(new Date(this.todayMidnight));
    this.updateFromRangeForUntilValue(d);
  }

  /**
   * Validate a date against a given interval
   * @param inDate - The date to validate
   * @param min - The minimum date
   * @param max - The maximum date
   * @returns a validation error with either minDate or maxDate set or null
   */
  #validateDateAgainstMinAndMax(
    inDate: Date,
    min: Date,
    max: Date,
  ): ValidationErrors | null {
    if (!inDate) return { invalid: true };
    if (inDate < min) {
      return { minDate: true };
    } else if (inDate > max) {
      return { maxDate: true };
    }
    return null;
  }

  /**
   * Validate a Form Control against the constraints of the date
   * @param control The Form Control to validate
   * @param isFromDate Whether the date is a 'from' date
   * @returns a validation error or null
   */
  #dateValidator = (
    control: AbstractControl<Date, Date>,
    isFromDate: boolean,
  ): ValidationErrors | null => {
    const [min, max, field, name] = isFromDate
      ? [this.minFromDate, this.maxFromDate, this.fromDateErrorMessage, 'start']
      : [this.minUntilDate, this.maxUntilDate, this.untilDateErrorMessage, 'end'];
    const ret = this.#validateDateAgainstMinAndMax(control.value, min, max);
    field.set(this.getErrorMessageForValidationState(name, ret));
    return ret;
  };

  readonly fromFormControl = new FormControl('', [
    Validators.required,
    (control) => this.#dateValidator(control, true),
  ]);

  readonly untilFormControl = new FormControl('', [
    Validators.required,
    (control) => this.#dateValidator(control, false),
  ]);

  /**
   * Get an error message for a given validation state
   * @param name - The name of the date (e.g. start or end)
   * @param error - The validation error with minDate, maxDate or invalid set
   * @returns an error message as a string
   */
  getErrorMessageForValidationState(
    name: string,
    error: ValidationErrors | null,
  ): string {
    if (!error) {
      return '';
    } else if (error['invalid']) {
      return 'Please choose a valid ' + name + ' date.';
    } else if (error['minDate']) {
      return 'Please choose a later ' + name + ' date.';
    } else if (error['maxDate']) {
      return 'Please choose an earlier ' + name + ' date.';
    } else {
      return '';
    }
  }

  /**
   * Update the error message for the description form control
   */
  updateDescriptionErrorMessage() {
    if (this.descriptionFormControl.hasError('required')) {
      this.descriptionErrorMessage.set('Please provide a reason for this request.');
    } else {
      this.descriptionErrorMessage.set('');
    }
  }

  /**
   * Update the error message based on the from date form control
   * @param $event - The event that triggered the change
   */
  fromDateChanged($event: MatDatepickerInputEvent<Date, string>) {
    if ($event.value) {
      this.updateUntilRangeForFromValue($event.value);
    }
  }

  /**
   * Update the error message based on the until date form control
   * @param $event - The event that triggered the change
   */
  untilDateChanged($event: MatDatepickerInputEvent<Date, string>) {
    if ($event.value) {
      this.updateFromRangeForUntilValue($event.value);
    }
  }

  /**
   * Update the range for the from date based on the until date
   * @param date - The until date to update the range for
   */
  updateFromRangeForUntilValue(date: Date): void {
    const currentDate = this.todayMidnight;

    const newFromMinDate = new Date(date);
    const dateMinusGrantMaxDays = new Date(date);
    dateMinusGrantMaxDays.setDate(date.getDate() - this.#config.accessGrantMaxDays);
    newFromMinDate.setTime(
      Math.max(dateMinusGrantMaxDays.getTime(), currentDate.getTime()),
    );

    const newFromMaxDate = new Date(date);
    const dateMinusGrantMinDays = new Date(date);
    dateMinusGrantMinDays.setDate(date.getDate() - this.#config.accessGrantMinDays);
    const currentDatePlusUpfrontMaxDays = new Date(currentDate);
    currentDatePlusUpfrontMaxDays.setDate(
      currentDate.getDate() + this.#config.accessUpfrontMaxDays,
    );
    newFromMaxDate.setTime(
      Math.min(
        dateMinusGrantMinDays.getTime(),
        currentDatePlusUpfrontMaxDays.getTime(),
      ),
    );

    this.minFromDate = newFromMinDate;
    this.maxFromDate = newFromMaxDate;
  }

  /**
   * Update the range for the until date based on the from date
   * @param date - The from date to update the range for
   */
  updateUntilRangeForFromValue(date: Date): void {
    const newUntilMinDate = new Date(date);
    newUntilMinDate.setHours(23, 59, 59, 999);
    newUntilMinDate.setDate(date.getDate() + this.#config.accessGrantMinDays);
    const newUntilMaxDate = new Date(date);
    newUntilMaxDate.setHours(23, 59, 59, 999);
    newUntilMaxDate.setDate(date.getDate() + this.#config.accessGrantMaxDays);

    this.minUntilDate = newUntilMinDate;
    this.maxUntilDate = newUntilMaxDate;
  }

  /**
   * Update the error message for the email form control
   */
  updateEmailErrorMessage(): void {
    if (this.emailFormControl.hasError('required')) {
      this.emailErrorMessage.set('You must enter an email address');
    } else if (this.emailFormControl.hasError('email')) {
      this.emailErrorMessage.set('Not a valid email');
    } else {
      this.emailErrorMessage.set('');
    }
  }

  /**
   * Close the dialog without submitting the data
   */
  cancel(): void {
    this.dialogRef.close(undefined);
  }

  /**
   * Submit the access request and close the dialog
   */
  submit(): void {
    const description = this.descriptionFormControl.value;
    const fromDate = this.fromDate();
    fromDate?.setHours(0, 0, 0, 0);
    const untilDate = this.untilDate();
    untilDate?.setHours(23, 59, 59, 999);
    const email = this.emailFormControl.value;
    const data = { ...this.data, description, fromDate, untilDate, email };
    this.dialogRef.close(data);
  }
}
