/**
 * This Component is the content of a dialog used to request access to a dataset
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
  signal,
} from '@angular/core';
import { email, form, FormField, required, validate } from '@angular/forms/signals';
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
import { AccessRequestDetailData } from '@app/access-requests/models/access-requests';
import { ConfigService } from '@app/shared/services/config';
import { DATE_INPUT_FORMAT_HINT, timeZoneToUTC } from '@app/shared/utils/date-formats';

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
    FormField,
    MatDialogModule,
    MatButtonModule,
  ],
  templateUrl: './access-request-dialog.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AccessRequestDialogComponent {
  readonly dialogRef = inject(MatDialogRef<AccessRequestDialogComponent>);
  readonly data = inject<AccessRequestDetailData>(MAT_DIALOG_DATA);
  #config = inject(ConfigService);
  readonly dateInputFormatHint = DATE_INPUT_FORMAT_HINT;
  protected model = signal({
    description: this.data.description ?? '',
    fromDate: null as Date | null,
    untilDate: null as Date | null,
    email: this.data.email ?? '',
  });
  readonly todayMidnight = new Date();
  datasetID = input.required<string>();
  protected minFromDate = signal(new Date());
  protected maxFromDate = signal(new Date());
  protected minUntilDate = signal(new Date());
  protected maxUntilDate = signal(new Date());
  protected requestForm = form(this.model, (p) => {
    required(p.description);
    required(p.email);
    email(p.email);
    validate(p.fromDate, ({ value }) => {
      const date = value();
      if (!date)
        return { kind: 'required', message: 'Please choose a valid start date.' };
      if (date < this.minFromDate())
        return { kind: 'minDate', message: 'Please choose a later start date.' };
      if (date > this.maxFromDate())
        return { kind: 'maxDate', message: 'Please choose an earlier start date.' };
      return null;
    });
    validate(p.untilDate, ({ value }) => {
      const date = value();
      if (!date)
        return { kind: 'required', message: 'Please choose a valid end date.' };
      if (date < this.minUntilDate())
        return { kind: 'minDate', message: 'Please choose a later end date.' };
      if (date > this.maxUntilDate())
        return { kind: 'maxDate', message: 'Please choose an earlier end date.' };
      return null;
    });
  });
  protected descriptionError = computed(() => {
    const f = this.requestForm.description();
    return f.touched() && f.invalid()
      ? 'Please provide a reason for this request.'
      : '';
  });
  protected emailError = computed(() => {
    const f = this.requestForm.email();
    if (!f.touched() || !f.invalid()) return '';
    return f.errors().find((e) => e.kind === 'required')
      ? 'You must enter an email address'
      : 'Not a valid email';
  });
  protected untilDateError = computed(
    () => this.requestForm.untilDate().errors()[0]?.message ?? '',
  );
  protected fromDateError = computed(
    () => this.requestForm.fromDate().errors()[0]?.message ?? '',
  );
  protected submitDisabled = computed(() => !this.requestForm().valid());

  constructor() {
    this.todayMidnight.setHours(0, 0, 0, 0);
    const defaultFromDate = new Date(this.todayMidnight);

    let d = new Date(this.todayMidnight);
    d.setHours(23, 59, 59, 999);
    d.setDate(d.getDate() + this.#config.defaultAccessDurationDays - 1);
    const defaultUntilDate = d;

    this.updateUntilRangeForFromValue(defaultFromDate);
    this.updateFromRangeForUntilValue(defaultUntilDate);

    this.model.update((m) => ({
      ...m,
      fromDate: defaultFromDate,
      untilDate: defaultUntilDate,
    }));
  }

  /**
   * Update the error message based on the from date form control
   * @param $event - The event that triggered the change
   */
  fromDateChanged($event: MatDatepickerInputEvent<Date, string>): void {
    if ($event.value) {
      this.updateUntilRangeForFromValue($event.value);
    }
  }

  /**
   * Update the error message based on the until date form control
   * @param $event - The event that triggered the change
   */
  untilDateChanged($event: MatDatepickerInputEvent<Date, string>): void {
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
    dateMinusGrantMaxDays.setDate(date.getDate() - this.#config.accessGrantMaxDays - 1);
    newFromMinDate.setTime(
      Math.max(dateMinusGrantMaxDays.getTime(), currentDate.getTime()),
    );

    const newFromMaxDate = new Date(date);
    const dateMinusGrantMinDays = new Date(date);
    dateMinusGrantMinDays.setDate(date.getDate() - this.#config.accessGrantMinDays);
    const currentDatePlusUpfrontMaxDays = new Date(currentDate);
    currentDatePlusUpfrontMaxDays.setDate(
      currentDate.getDate() + this.#config.accessUpfrontMaxDays - 1,
    );
    newFromMaxDate.setTime(
      Math.min(
        dateMinusGrantMinDays.getTime(),
        currentDatePlusUpfrontMaxDays.getTime(),
      ),
    );

    this.minFromDate.set(newFromMinDate);
    this.maxFromDate.set(newFromMaxDate);
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
    newUntilMaxDate.setDate(date.getDate() + this.#config.accessGrantMaxDays - 1);

    this.minUntilDate.set(newUntilMinDate);
    this.maxUntilDate.set(newUntilMaxDate);
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
    if (!this.requestForm().valid()) return;
    const { description, email: emailValue, fromDate, untilDate } = this.model();
    if (!fromDate || !untilDate) return;
    const from = timeZoneToUTC(
      fromDate.getFullYear(),
      fromDate.getMonth(),
      fromDate.getDate(),
    );
    const until = timeZoneToUTC(
      untilDate.getFullYear(),
      untilDate.getMonth(),
      untilDate.getDate(),
      true,
    );
    this.dialogRef.close({
      ...this.data,
      description,
      fromDate: from,
      untilDate: until,
      email: emailValue,
    });
  }
}
