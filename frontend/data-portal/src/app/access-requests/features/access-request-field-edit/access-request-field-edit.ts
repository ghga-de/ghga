/**
 * This component is an editor for one of the access request fields.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import {
  Component,
  computed,
  effect,
  inject,
  input,
  linkedSignal,
  OnInit,
  output,
  signal,
} from '@angular/core';
import { form, FormField, validate } from '@angular/forms/signals';
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
    FormField,
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

  saved = output<Map<keyof AccessRequest, string>>();
  edited = output<[keyof AccessRequest, boolean]>();

  isOpen = signal<boolean>(false);

  /**
   * The form model. For a ticket ID, it removes a prefix taken from (parts of)
   * the base ticket URL, so that a pasted ticket link becomes its ID.
   */
  protected formModel = linkedSignal(() => ({ field: '' }), {
    set: (model, rawSet) => rawSet({ ...model, field: this.#ticketId(model.field) }),
  });

  protected fieldForm = form(this.formModel, (p) => {
    validate(p.field, ({ value }) => {
      if (this.name() !== 'ticket_id') return null;
      return new RegExp(PATTERN_TICKET_ID).test(value())
        ? null
        : { kind: 'pattern', message: ERROR_TICKET_ID };
    });
  });

  validationError = computed(() => this.fieldForm.field().errors()[0]?.message ?? '');

  ticketUrl = computed<string | null>(() =>
    this.name() === 'ticket_id' && this.formModel().field
      ? this.#baseTicketUrl + this.formModel().field
      : null,
  );

  #defaultValue = computed<string>(() => this.request()[this.name()] || '');

  isModified = computed<boolean>(
    () => this.isOpen() && this.formModel().field !== this.#defaultValue(),
  );

  /**
   * Remove a prefix taken from (parts of) the base ticket URL from a ticket ID
   * @param value - the value entered into the field
   * @returns the value without that prefix, or unchanged for other fields
   */
  #ticketId(value: string): string {
    if (this.name() !== 'ticket_id') return value;
    const baseUrl = this.#baseTicketUrl;
    const i = value.lastIndexOf('/');
    return baseUrl && i >= 0 && baseUrl.endsWith(value.substring(0, i + 1))
      ? value.substring(i + 1)
      : value;
  }

  /**
   * Notify the parent whenever the pending-edit state of this field changes.
   */
  #editedEffect = effect(() => this.edited.emit([this.name(), this.isModified()]));

  /**
   * Populate the editable field with the values from the access request on component init.
   */
  ngOnInit(): void {
    this.formModel.set({ field: this.#defaultValue() });
  }

  edit = () => {
    this.isOpen.set(true);
  };

  cancel = () => {
    if (this.isModified()) {
      this.formModel.set({ field: this.#defaultValue() });
    }
    this.isOpen.set(false);
  };

  save = () => {
    if (this.isModified()) {
      this.saved.emit(new Map([[this.name(), this.formModel().field]]));
    }
    this.isOpen.set(false);
  };
}
