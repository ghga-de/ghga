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

const MILLISECONDS_PER_DAY = 86400000;

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
  styleUrl: './access-request-dialog.component.scss',
})
export class AccessRequestDialogComponent {
  readonly emailFormControl = new FormControl('', [
    Validators.required,
    Validators.email,
  ]);
  readonly descriptionFormControl = new FormControl('', [Validators.required]);
  readonly dialogRef = inject(MatDialogRef<AccessRequestDialogComponent>);
  readonly data = inject<AccessRequestDialogData>(MAT_DIALOG_DATA);
  #config = inject(ConfigService);
  readonly result = model(this.data);
  readonly email = model(this.data.email);
  readonly description = model(this.data.description);
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
    this.fromDate.set(this.todayMidnight);
    let d = new Date();
    d.setDate(d.getDate() + this.#config.default_access_duration_days);
    this.untilDate.set(d);
    this.minUntilDate.setDate(
      this.minUntilDate.getDate() + this.#config.access_grant_min_days,
    );
    this.updateUntilRangeForFromValue(new Date());
    this.updateFromRangeForUntilValue(d);
  }

  /**
   * This function takes a From Control to validate it against the constraints of the from date
   * @param control The form Control to validate
   * @returns a validation error or null
   */
  fromDateValidator = (
    control: AbstractControl<Date, Date>,
  ): ValidationErrors | null => {
    const ret = this.validateDateAgainstMinAndMax(
      control.value,
      this.minFromDate,
      this.maxFromDate,
    );
    this.fromDateErrorMessage.set(this.getErrorMessageForValidationState('start', ret));
    return ret;
  };

  /**
   * This function takes a From Control to validate it against the constraints of the until date
   * @param control The form Control to validate
   * @returns a validation error or null
   */
  untilDateValidator = (
    control: AbstractControl<Date, Date>,
  ): ValidationErrors | null => {
    const ret = this.validateDateAgainstMinAndMax(
      control.value,
      this.minUntilDate,
      this.maxUntilDate,
    );
    this.untilDateErrorMessage.set(this.getErrorMessageForValidationState('end', ret));
    return ret;
  };

  getErrorMessageForValidationState = (
    name: string,
    error: ValidationErrors | null,
  ): string => {
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
  };

  validateDateAgainstMinAndMax = (
    inDate: Date,
    min: Date,
    max: Date,
  ): ValidationErrors | null => {
    if (!inDate) return { invalid: true };
    if (inDate < min) {
      return { minDate: true };
    } else if (inDate > max) {
      return { maxDate: true };
    }
    return null;
  };

  /**
   * The form controls need to be defined AFTER the previous functions because of the scope binding of this.
   */
  readonly fromFormControl = new FormControl('', [
    Validators.required,
    this.fromDateValidator.bind(this),
  ]);
  readonly untilFormControl = new FormControl('', [
    Validators.required,
    this.untilDateValidator.bind(this),
  ]);

  updateDescriptionErrorMessage = () => {
    if (this.descriptionFormControl.hasError('required')) {
      this.descriptionErrorMessage.set('Please provide a reason for this request.');
    } else {
      this.descriptionErrorMessage.set('');
    }
  };

  fromDateChanged = ($event: MatDatepickerInputEvent<Date, string>) => {
    if ($event.value) {
      this.updateUntilRangeForFromValue($event.value);
    }
  };

  untilDateChanged = ($event: MatDatepickerInputEvent<Date, string>) => {
    if ($event.value) {
      this.updateFromRangeForUntilValue($event.value);
    }
  };

  updateFromRangeForUntilValue = (date: Date) => {
    const currentDate = this.todayMidnight;

    const newFromMinDate = new Date(
      Math.max(
        currentDate.getTime(),
        date.getTime() - this.#config.access_grant_max_days * MILLISECONDS_PER_DAY,
      ),
    );
    const newFromMaxDate = new Date(
      Math.min(
        date.getTime() - this.#config.access_grant_min_days * MILLISECONDS_PER_DAY,
        currentDate.getTime() +
          this.#config.access_upfront_max_days * MILLISECONDS_PER_DAY,
      ),
    );

    this.minFromDate = newFromMinDate;
    this.maxFromDate = newFromMaxDate;
  };

  updateUntilRangeForFromValue = (date: Date) => {
    const newUntilMinDate = new Date(
      date.getTime() + this.#config.access_grant_min_days * MILLISECONDS_PER_DAY,
    );
    const newUntilMaxDate = new Date(
      date.getTime() + this.#config.access_grant_max_days * MILLISECONDS_PER_DAY,
    );

    this.minUntilDate = newUntilMinDate;
    this.maxUntilDate = newUntilMaxDate;
  };

  cancelClick = () => {
    this.dialogRef.close(undefined);
  };

  submitClick = () => {
    this.dialogRef.close(this.data);
  };

  updateEmailErrorMessage = () => {
    if (this.emailFormControl.hasError('required')) {
      this.emailErrorMessage.set('You must enter an email address');
    } else if (this.emailFormControl.hasError('email')) {
      this.emailErrorMessage.set('Not a valid email');
    } else {
      this.emailErrorMessage.set('');
    }
  };
}
