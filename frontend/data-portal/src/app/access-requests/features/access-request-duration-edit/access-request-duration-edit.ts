/**
 * This component is an editor for the duration of an access request.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DatePipe as CommonDatePipe } from '@angular/common';
import {
  Component,
  computed,
  inject,
  input,
  model,
  OnInit,
  output,
  signal,
} from '@angular/core';
import {
  AbstractControl,
  FormControl,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';
import { MatChipsModule } from '@angular/material/chips';
import {
  MatDatepickerInputEvent,
  MatDatepickerModule,
} from '@angular/material/datepicker';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { AccessRequest } from '@app/access-requests/models/access-requests';
import { DatePipe } from '@app/shared/pipes/date-pipe';
import { ConfigService } from '@app/shared/services/config';
import {
  DEFAULT_DATE_OUTPUT_FORMAT,
  DEFAULT_TIME_ZONE,
  timeZoneToUTC,
} from '@app/shared/utils/date-formats';

/**
 * Editor for the duration of access requests.
 */
@Component({
  selector: 'app-access-request-duration-edit',
  imports: [
    MatDatepickerModule,
    MatChipsModule,
    MatIconModule,
    MatInputModule,
    DatePipe,
    ReactiveFormsModule,
  ],
  providers: [CommonDatePipe],
  templateUrl: './access-request-duration-edit.html',
})
export class AccessRequestDurationEditComponent implements OnInit {
  #config = inject(ConfigService);
  maxDays = this.#config.accessGrantMaxDays;
  maxExtend = this.#config.accessGrantMaxExtend;
  defaultDuration = this.#config.defaultAccessDurationDays;

  readonly periodFormat = DEFAULT_DATE_OUTPUT_FORMAT;
  readonly periodTimeZone = DEFAULT_TIME_ZONE;

  request = input.required<AccessRequest>();

  locked = computed<boolean>(() => this.request().status !== 'pending');

  fromField = model<Date>();
  untilField = model<Date>();

  saved = output<Map<keyof AccessRequest, string>>();
  edited = output<[keyof AccessRequest, boolean]>();

  isOpen = signal<boolean>(false);
  isModified = signal<boolean>(false);

  todayStart = new Date();
  todayEnd = new Date();
  minFromDate = new Date();
  minUntilDate = new Date();
  maxFromDate = new Date();
  maxUntilDate = new Date();

  fromFieldErrorMessage = signal<string | null>(null);
  untilFieldErrorMessage = signal<string | null>(null);

  #defaultFromDate = computed<Date>(() => {
    const date = new Date();
    date.setHours(0, 0, 0, 0);
    if (new Date(this.request()['access_starts']) < date) {
      return date;
    }
    const midnightDefault = new Date(this.request()['access_starts']);
    midnightDefault.setHours(0, 0, 0, 0);
    return midnightDefault;
  });
  #defaultUntilDate = computed<Date>(() => {
    const date = new Date();
    date.setHours(23, 59, 59, 999);
    if (new Date(this.request()['access_ends']) < date) {
      return date;
    }
    const midnightDefault = new Date(this.request()['access_ends']);
    midnightDefault.setHours(23, 59, 59, 999);
    return midnightDefault;
  });

  fromFormControl: FormControl<Date | null> = new FormControl<Date | null>(null);
  untilFormControl: FormControl<Date | null> = new FormControl<Date | null>(null);

  constructor() {
    this.todayStart.setHours(0, 0, 0, 0);
    this.todayEnd.setHours(23, 59, 59, 999);
  }

  /**
   * Populate the access start and end fields with the values from the access request on component init.
   */
  ngOnInit(): void {
    this.fromField.update(() => {
      if (this.#defaultFromDate() < this.todayStart) return new Date(this.todayStart);
      return new Date(this.#defaultFromDate());
    });

    this.untilField.update(() => {
      if (this.#defaultUntilDate() < this.todayEnd) return new Date(this.todayEnd);
      return new Date(this.#defaultUntilDate());
    });

    this.updateAccessStartRanges(new Date(this.untilField() ?? new Date()));
    this.updateAccessEndRanges(new Date(this.fromField() ?? new Date()));

    const initialFrom = this.fromField() ?? this.#defaultFromDate();
    const initialUntil = this.untilField() ?? this.#defaultUntilDate();

    this.fromFormControl = new FormControl<Date | null>(initialFrom, [
      Validators.required,
      (control) => this.#fromDateValidator(control),
    ]);
    this.untilFormControl = new FormControl<Date | null>(initialUntil, [
      Validators.required,
      (control) => this.#untilDateValidator(control),
    ]);

    this.fromFormControl.updateValueAndValidity();
    this.untilFormControl.updateValueAndValidity();
  }

  /**
   * Update the range for the until date based on the from date
   * @param date - The from date to update the range for
   */
  updateAccessEndRanges(date: Date): void {
    const dateAfterNextDay = new Date(this.todayStart);
    this.minUntilDate = dateAfterNextDay;

    const newUntilMaxDate = new Date(date);
    newUntilMaxDate.setHours(23, 59, 59, 999);
    newUntilMaxDate.setDate(date.getDate() + Math.round(this.maxDays * this.maxExtend));
    this.maxUntilDate = newUntilMaxDate;
  }

  /**
   * Update the range for the from date based on the until date
   * @param date - The until date to update the range for
   */
  updateAccessStartRanges(date: Date): void {
    const currentDate = new Date(this.todayStart);

    const newFromMinDate = new Date();
    const dateMinusGrantMaxDays = new Date(date);
    dateMinusGrantMaxDays.setDate(date.getDate() - this.maxDays * this.maxExtend);
    if (currentDate < dateMinusGrantMaxDays)
      newFromMinDate.setTime(dateMinusGrantMaxDays.getTime());
    else newFromMinDate.setTime(currentDate.getTime());

    const newFromMaxDate = new Date();
    const dateMinusOneDay = new Date(date);
    dateMinusOneDay.setHours(0, 0, 0, 0);
    newFromMaxDate.setTime(dateMinusOneDay.getTime());

    this.minFromDate = newFromMinDate;
    this.maxFromDate = newFromMaxDate;
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
    if (!inDate || min > max) return { invalid: true };
    if (inDate < min) {
      return { minDate: true };
    } else if (inDate > max) {
      return { maxDate: true };
    }
    return null;
  }

  /**
   * Get an error message for a given validation state
   * @param name - The name of the date (e.g. start or end)
   * @param error - The validation error with minDate, maxDate or invalid set
   * @returns an error message as a string
   */
  getErrorMessageForValidationState(
    name: string,
    error: ValidationErrors | null,
  ): string | null {
    if (!error) {
      return null;
    } else if (error['invalid']) {
      return 'Invalid ' + name + ' date';
    } else if (error['minDate']) {
      return 'Too early ' + name + ' date';
    } else if (error['maxDate']) {
      return 'Too late ' + name + ' date';
    } else {
      return 'Invalid ' + name + ' date';
    }
  }

  /**
   * Validate a Form Control against the constraints of the from date
   * @param control The form Control to validate
   * @returns a validation error or null
   */
  #fromDateValidator = (
    control: AbstractControl<Date, Date>,
  ): ValidationErrors | null => {
    const ret = this.#validateDateAgainstMinAndMax(
      control.value,
      this.minFromDate,
      this.maxFromDate,
    );
    this.fromFieldErrorMessage.set(
      this.getErrorMessageForValidationState('start', ret),
    );
    return ret;
  };

  /**
   * Validate a Form Control against the constraints of the until date
   * @param control The form Control to validate
   * @returns a validation error or null
   */
  #untilDateValidator = (
    control: AbstractControl<Date, Date>,
  ): ValidationErrors | null => {
    const ret = this.#validateDateAgainstMinAndMax(
      control.value,
      this.minUntilDate,
      this.maxUntilDate,
    );
    this.untilFieldErrorMessage.set(this.getErrorMessageForValidationState('end', ret));
    return ret;
  };

  open = () => {
    this.isOpen.set(true);
  };

  onDateSelected = (
    selectedDate: MatDatepickerInputEvent<Date> | Date,
    isFromDate: boolean,
  ) => {
    let value: Date | null = null;
    if (selectedDate instanceof MatDatepickerInputEvent) value = selectedDate.value;
    else value = selectedDate;
    if (value) {
      const selectedLocalDate = new Date(value);
      if (isFromDate) {
        selectedLocalDate.setHours(0, 0, 0, 0);
        this.updateAccessEndRanges(selectedLocalDate);
        this.fromField.set(selectedLocalDate);
        this.fromFormControl.setValue(selectedLocalDate);
        this.untilFormControl.updateValueAndValidity();
      } else {
        selectedLocalDate.setHours(23, 59, 59, 999);
        this.updateAccessStartRanges(selectedLocalDate);
        this.untilField.set(selectedLocalDate);
        this.untilFormControl.setValue(selectedLocalDate);
        this.fromFormControl.updateValueAndValidity();
      }
      this.changed();
    } else {
      this.fromField.set(this.#defaultFromDate());
      this.fromFormControl.setValue(this.fromField() ?? null);
      this.untilFormControl.updateValueAndValidity();
      this.changed();
    }
  };

  saveDisabled = () => {
    return this.fromFieldErrorMessage() || this.untilFieldErrorMessage();
  };

  changed = () => {
    const wasModified = this.isModified();
    const isModified = this.fromField() !== this.#defaultFromDate();
    if (isModified !== wasModified) {
      this.isModified.set(isModified);
      this.edited.emit(['access_ends', isModified]);
    }
  };

  cancel = () => {
    if (this.isModified()) {
      this.fromField.update(() => this.#defaultFromDate());
      this.untilField.update(() => this.#defaultUntilDate());
      this.edited.emit(['access_ends', false]);
    }
    this.isOpen.set(false);
  };

  save = () => {
    if (this.fromField() && this.untilField()) {
      this.onDateSelected(new Date(this.fromField() as Date), true);
      this.onDateSelected(new Date(this.untilField() as Date), false);
      const from = new Date(this.fromField()!);
      const until = new Date(this.untilField()!);
      const fromDate = timeZoneToUTC(
        from.getFullYear(),
        from.getMonth(),
        from.getDate(),
      );
      const untilDate = timeZoneToUTC(
        until.getFullYear(),
        until.getMonth(),
        until.getDate(),
        true,
      );
      if (from && until) {
        const fromISO = fromDate.toISOString();
        const untilISO = untilDate.toISOString();
        if (this.isModified()) {
          const saveMap = new Map<keyof AccessRequest, string>();
          saveMap.set('access_starts', fromISO);
          saveMap.set('access_ends', untilISO);
          this.saved.emit(saveMap);
          this.edited.emit(['access_ends', false]);
        }
        this.isOpen.set(false);
      }
    }
  };
}
