/**
 * This component is an editor for one of the access request fields.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DatePipe } from '@angular/common';
import {
  Component,
  computed,
  effect,
  inject,
  input,
  model,
  output,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatChipsModule } from '@angular/material/chips';
import {
  MatDatepickerInputEvent,
  MatDatepickerModule,
} from '@angular/material/datepicker';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { AccessRequest } from '@app/access-requests/models/access-requests';
import { ConfigService } from '@app/shared/services/config.service';

/**
 * Editor for one of the fields of AccessRequest.
 */
@Component({
  selector: 'app-access-request-field-edit',
  imports: [
    MatDatepickerModule,
    MatChipsModule,
    MatIconModule,
    MatInputModule,
    FormsModule,
    DatePipe,
  ],
  templateUrl: './access-request-field-edit.component.html',
  styleUrl:
    '../access-request-manager-dialog/access-request-manager-dialog.component.scss',
})
export class AccessRequestFieldEditComponent {
  #config = inject(ConfigService);
  #baseTicketUrl = this.#config.helpdeskTicketUrl;

  request = input.required<AccessRequest>();

  name = input.required<keyof AccessRequest>();
  label = input.required<string>();

  isDate = input<boolean>(false);

  rows = computed<number>(() => (this.name().includes('note') ? 5 : 1));
  locked = computed<boolean>(() => this.request().status !== 'pending');

  field = model<string>('');

  saved = output<[keyof AccessRequest, string]>();
  edited = output<[keyof AccessRequest, boolean]>();

  isOpen = signal<boolean>(false);
  isModified = signal<boolean>(false);

  ticketUrl = computed<string | null>(() =>
    this.name() == 'ticket_id' && this.field()
      ? this.#baseTicketUrl + this.field()
      : null,
  );

  #defaultValue = computed<string>(() => (this.request() as any)[this.name()] || '');

  #initFieldEffect = effect(() => this.field.update(() => this.#defaultValue()));

  #getValue = () => {
    const name = this.name();
    let value = this.field();
    if (name === 'ticket_id' && value && value.startsWith(this.#baseTicketUrl)) {
      value = value.slice(this.#baseTicketUrl.length);
    }
    return value;
  };

  edit = () => {
    this.isOpen.set(true);
  };

  onDateSelected = (event: MatDatepickerInputEvent<Date>) => {
    if (event.value) {
      const selectedLocalDate = event.value;

      const utcDateMidnight = new Date(
        Date.UTC(
          selectedLocalDate.getFullYear(),
          selectedLocalDate.getMonth(),
          selectedLocalDate.getDate(),
        ),
      );
      this.field.set(utcDateMidnight.toISOString());
      this.changed();
    } else {
      this.field.set('');
      this.changed();
    }
  };

  changed = () => {
    const wasModified = this.isModified();
    const isModified = this.#getValue() !== this.#defaultValue();
    if (isModified !== wasModified) {
      this.isModified.set(isModified);
      this.edited.emit([this.name(), isModified]);
    }
  };

  cancel = () => {
    if (this.isModified()) {
      this.field.update(() => this.#defaultValue());
      this.edited.emit([this.name(), false]);
    }
    this.isOpen.set(false);
  };

  save = () => {
    const name = this.name();
    const value = this.#getValue();
    this.field.update(() => value);
    if (this.isModified()) {
      this.saved.emit([name, value]);
      this.edited.emit([name, false]);
    }
    this.isOpen.set(false);
  };
}
