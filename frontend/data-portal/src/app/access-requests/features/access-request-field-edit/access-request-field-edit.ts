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
import { FormControl, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatChipsModule } from '@angular/material/chips';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { AccessRequest } from '@app/access-requests/models/access-requests';
import { ConfigService } from '@app/shared/services/config';
import { ExternalLinkDirective } from '@app/shared/ui/external-link/external-link';

// we assume that ticket IDs are integers with up to 9 digits
const PATTERN_TICKET_ID = '^[0-9]{0,9}$';
const ERROR_TICKET_ID = 'ID must be a number with up to 9 digits';

/**
 * Editor for one of the fields of AccessRequest.
 */
@Component({
  selector: 'app-access-request-field-edit',
  imports: [
    ExternalLinkDirective,
    MatDatepickerModule,
    MatChipsModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    FormsModule,
    ReactiveFormsModule,
  ],
  templateUrl: './access-request-field-edit.html',
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

  pattern = computed<string>(() =>
    this.name() === 'ticket_id' ? PATTERN_TICKET_ID : '.*',
  );
  validationError = signal<string>('');

  ticketUrl = computed<string | null>(() =>
    this.name() === 'ticket_id' && this.field()
      ? this.#baseTicketUrl + this.field()
      : null,
  );

  #defaultValue = computed<string>(() => this.request()[this.name()] || '');

  /**
   * Populate the editable field with the values from the access request on component init.
   */
  ngOnInit(): void {
    this.field.update(() => this.#defaultValue());
  }

  edit = () => {
    this.isOpen.set(true);
  };

  /**
   * Remove any URL prefix from the field value if this is a ticket ID
   * and set the proper error message if the field is invalid.
   * @param control - the form control for the field
   */
  #handleControl = (control: FormControl) => {
    if (this.name() === 'ticket_id') {
      // if the field is prefixed with (parts of) the base ticket URL, remove that prefix
      const baseUrl = this.#baseTicketUrl;
      let value = this.field() || '';
      const i = value.lastIndexOf('/');
      if (baseUrl && i >= 0 && baseUrl.endsWith(value.substring(0, i + 1))) {
        value = value.substring(i + 1);
        control.setValue(value);
      }
      this.validationError.set(control.invalid ? ERROR_TICKET_ID : '');
    }
  };

  changed = (control?: FormControl) => {
    if (control) this.#handleControl(control);
    const wasModified = this.isModified();
    const isModified = this.field() !== this.#defaultValue();
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
    const field = this.field();
    if (field === undefined) return;
    this.field.update(() => field);
    if (this.isModified()) {
      const name = this.name();
      this.saved.emit(new Map([[name, field]]));
      this.edited.emit([name, false]);
    }
    this.isOpen.set(false);
  };
}
