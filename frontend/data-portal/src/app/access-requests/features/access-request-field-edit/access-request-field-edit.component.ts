/**
 * This component is an editor for one of the access request fields.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

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
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatChipsModule } from '@angular/material/chips';
import { MatDatepickerModule } from '@angular/material/datepicker';
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
    ReactiveFormsModule,
  ],
  templateUrl: './access-request-field-edit.component.html',
  styleUrl: './access-request-field-edit.component.scss',
})
export class AccessRequestFieldEditComponent implements OnInit {
  #config = inject(ConfigService);
  #baseTicketUrl = this.#config.helpdeskTicketUrl;

  request = input.required<AccessRequest>();

  name = input.required<keyof AccessRequest>();
  label = input.required<string>();

  rows = computed<number>(() => (this.name().includes('note') ? 5 : 1));
  locked = computed<boolean>(() => this.request().status !== 'pending');

  field = model<string>();

  saved = output<Map<keyof AccessRequest, string>>();
  edited = output<[keyof AccessRequest, boolean]>();

  isOpen = signal<boolean>(false);
  isModified = signal<boolean>(false);

  ticketUrl = computed<string | null>(() =>
    this.name() === 'ticket_id' ? this.#baseTicketUrl + this.field() : null,
  );

  #defaultValue = computed<string>(() => this.request()[this.name()] || '');

  /**
   * Populate the editable field with the values from the access request on component init.
   */
  ngOnInit(): void {
    this.field.update(() => this.#defaultValue());
  }

  #getValue = () => {
    if (
      this.name() === 'ticket_id' &&
      this.field() &&
      (this.field() as string).startsWith(this.#baseTicketUrl)
    ) {
      this.field.set((this.field() as string).slice(this.#baseTicketUrl.length));
    }
    return this.field();
  };

  edit = () => {
    this.isOpen.set(true);
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
    if (this.field()) {
      this.field.update(() => this.field());
      if (this.isModified()) {
        this.saved.emit(new Map([[this.name(), this.field() as string]]));
        this.edited.emit([this.name(), false]);
      }
      this.isOpen.set(false);
    }
  };
}
