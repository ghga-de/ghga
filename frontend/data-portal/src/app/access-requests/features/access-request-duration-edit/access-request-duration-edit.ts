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
  OnInit,
  output,
  signal,
} from '@angular/core';
import { form, FormField, validate } from '@angular/forms/signals';
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
    FormField,
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

  saved = output<Map<keyof AccessRequest, string>>();
  edited = output<[keyof AccessRequest, boolean]>();

  isOpen = signal<boolean>(false);
  isModified = signal<boolean>(false);

  todayStart = new Date();
  todayEnd = new Date();

  protected minFromDate = signal(new Date());
  protected maxFromDate = signal(new Date());
  protected minUntilDate = signal(new Date());
  protected maxUntilDate = signal(new Date());

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

  protected formModel = signal({
    fromDate: null as Date | null,
    untilDate: null as Date | null,
  });

  protected durationForm = form(this.formModel, (p) => {
    validate(p.fromDate, ({ value }) => {
      const date = value();
      if (!date) return { kind: 'required', message: 'Invalid start date' };
      if (date < this.minFromDate())
        return { kind: 'minDate', message: 'Too early start date' };
      if (date > this.maxFromDate())
        return { kind: 'maxDate', message: 'Too late start date' };
      return null;
    });
    validate(p.untilDate, ({ value }) => {
      const date = value();
      if (!date) return { kind: 'required', message: 'Invalid end date' };
      if (date < this.minUntilDate())
        return { kind: 'minDate', message: 'Too early end date' };
      if (date > this.maxUntilDate())
        return { kind: 'maxDate', message: 'Too late end date' };
      return null;
    });
  });

  protected fromDateError = computed(
    () => this.durationForm.fromDate().errors()[0]?.message ?? null,
  );
  protected untilDateError = computed(
    () => this.durationForm.untilDate().errors()[0]?.message ?? null,
  );

  constructor() {
    this.todayStart.setHours(0, 0, 0, 0);
    this.todayEnd.setHours(23, 59, 59, 999);
  }

  /**
   * Populate the access start and end fields with the values from the access request on component init.
   */
  ngOnInit(): void {
    const initialFrom =
      this.#defaultFromDate() < this.todayStart
        ? new Date(this.todayStart)
        : new Date(this.#defaultFromDate());

    const initialUntil =
      this.#defaultUntilDate() < this.todayEnd
        ? new Date(this.todayEnd)
        : new Date(this.#defaultUntilDate());

    this.updateAccessStartRanges(initialUntil);
    this.updateAccessEndRanges(initialFrom);

    this.formModel.set({ fromDate: initialFrom, untilDate: initialUntil });
  }

  /**
   * Update the range for the until date based on the from date
   * @param date - The from date to update the range for
   */
  updateAccessEndRanges(date: Date): void {
    this.minUntilDate.set(new Date(this.todayStart));

    const newUntilMaxDate = new Date(date);
    newUntilMaxDate.setHours(23, 59, 59, 999);
    newUntilMaxDate.setDate(date.getDate() + Math.round(this.maxDays * this.maxExtend));
    this.maxUntilDate.set(newUntilMaxDate);
  }

  /**
   * Update the range for the from date based on the until date
   * @param date - The until date to update the range for
   */
  updateAccessStartRanges(date: Date): void {
    const currentDate = new Date(this.todayStart);

    const dateMinusGrantMaxDays = new Date(date);
    dateMinusGrantMaxDays.setDate(date.getDate() - this.maxDays * this.maxExtend);
    const newFromMinDate = new Date(
      Math.max(dateMinusGrantMaxDays.getTime(), currentDate.getTime()),
    );

    const dateMinusOneDay = new Date(date);
    dateMinusOneDay.setHours(0, 0, 0, 0);
    this.minFromDate.set(newFromMinDate);
    this.maxFromDate.set(dateMinusOneDay);
  }

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
        this.formModel.update((m) => ({ ...m, fromDate: selectedLocalDate }));
      } else {
        selectedLocalDate.setHours(23, 59, 59, 999);
        this.updateAccessStartRanges(selectedLocalDate);
        this.formModel.update((m) => ({ ...m, untilDate: selectedLocalDate }));
      }
      this.changed();
    } else {
      this.formModel.update((m) => ({ ...m, fromDate: this.#defaultFromDate() }));
      this.changed();
    }
  };

  saveDisabled = () => !this.durationForm().valid();

  changed = () => {
    const wasModified = this.isModified();
    const isModified = this.formModel().fromDate !== this.#defaultFromDate();
    if (isModified !== wasModified) {
      this.isModified.set(isModified);
      this.edited.emit(['access_ends', isModified]);
    }
  };

  cancel = () => {
    if (this.isModified()) {
      this.formModel.set({
        fromDate: this.#defaultFromDate(),
        untilDate: this.#defaultUntilDate(),
      });
      this.edited.emit(['access_ends', false]);
    }
    this.isOpen.set(false);
  };

  save = () => {
    const { fromDate: selectedFrom, untilDate: selectedUntil } = this.formModel();
    if (selectedFrom && selectedUntil) {
      const from = new Date(selectedFrom);
      const until = new Date(selectedUntil);
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
