/**
 * Dialog for sending an SMS with a verification code to the DAC
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Clipboard } from '@angular/cdk/clipboard';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, effect, inject, signal, untracked } from '@angular/core';
import {
  form,
  FormField,
  maxLength,
  pattern,
  required,
  validate,
} from '@angular/forms/signals';
import { MatButtonModule } from '@angular/material/button';
import {
  MAT_DIALOG_DATA,
  MatDialogActions,
  MatDialogContent,
  MatDialogRef,
  MatDialogTitle,
} from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatTooltipModule } from '@angular/material/tooltip';
import { AccessRequest } from '@app/access-requests/models/access-requests';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { Notifier } from '@app/shared/services/notification';
import { generateVerificationCode } from '@app/shared/utils/verification-code';
import { NgxMatInputTelComponent } from 'ngx-mat-input-tel';

/** Maximum length of the SMS text, as accepted by the backend */
export const MAX_SMS_LENGTH = 480;

/**
 * Build the default text of the verification SMS.
 * @param ar - the access request to be confirmed
 * @param code - the verification code
 * @returns the text of the SMS
 */
export function verificationSmsText(ar: AccessRequest, code: string): string {
  const ticket = ar.ticket_id ? `, quoting ticket ${ar.ticket_id}` : '';
  return (
    `GHGA: To confirm the DAC approval of the access request of ${ar.full_user_name}` +
    ` for dataset ${ar.dataset_id}, please send the code ${code}` +
    ` to helpdesk@ghga.de${ticket}.`
  );
}

/**
 * Dialog that lets a data steward send an SMS with a verification code to a person
 * authorized to act for the DAC, who confirms the approval of the access request
 * by sending the code back to the helpdesk.
 *
 * The code is generated, but can be changed. The text follows the code until it
 * is edited by hand. The dialog closes with the new internal note of the request,
 * in which the backend records the sending.
 */
@Component({
  selector: 'app-verification-sms-dialog',
  imports: [
    FormField,
    MatDialogTitle,
    MatDialogContent,
    MatDialogActions,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatTooltipModule,
    NgxMatInputTelComponent,
  ],
  templateUrl: './verification-sms-dialog.html',
})
export class VerificationSmsDialog {
  #dialogRef = inject(MatDialogRef<VerificationSmsDialog, string | null>);
  #accessRequestService = inject(AccessRequestService);
  #notify = inject(Notifier);
  #clipboard = inject(Clipboard);

  protected request = inject<AccessRequest>(MAT_DIALOG_DATA);
  protected readonly maxLength = MAX_SMS_LENGTH;

  protected isSubmitting = signal(false);
  protected sendError = signal('');

  #initialCode = generateVerificationCode();

  protected smsModel = signal({
    phone: '',
    code: this.#initialCode,
    text: verificationSmsText(this.request, this.#initialCode),
  });

  protected smsForm = form(this.smsModel, (p) => {
    // the phone input emits E.164; the backend validates the number fully
    required(p.phone);
    required(p.code);
    pattern(p.code, /^[A-Za-z0-9]{4,16}$/);
    required(p.text);
    maxLength(p.text, MAX_SMS_LENGTH);
    validate(p.text, ({ value, valueOf }) =>
      value().includes(valueOf(p.code)) ? null : { kind: 'missingCode' },
    );
  });

  protected textLength = computed(() => this.smsModel().text.length);

  protected textMissesCode = computed(() =>
    this.smsForm
      .text()
      .errors()
      .some((e) => e.kind === 'missingCode'),
  );

  protected isSubmitDisabled = computed(
    () => !this.smsForm().valid() || this.isSubmitting(),
  );

  #code = computed(() => this.smsModel().code);

  // the text that was last generated, to tell whether it has been edited by hand
  #generatedText = this.smsModel().text;

  /**
   * Let the text follow the code as long as it has not been edited by hand.
   */
  #followCodeEffect = effect(() => {
    const code = this.#code();
    untracked(() => {
      if (this.smsModel().text === this.#generatedText) {
        this.#setGeneratedText(code);
      }
    });
  });

  /**
   * Replace the text with the generated text for the given code.
   * @param code - the verification code
   */
  #setGeneratedText(code: string): void {
    const text = verificationSmsText(this.request, code);
    this.#generatedText = text;
    this.smsModel.update((m) => ({ ...m, text }));
  }

  /**
   * Generate a new code.
   */
  protected regenerateCode(): void {
    const code = generateVerificationCode();
    this.smsModel.update((m) => ({ ...m, code }));
  }

  /**
   * Discard edits of the text and use the generated text again.
   */
  protected resetText(): void {
    this.#setGeneratedText(this.smsModel().code);
  }

  /**
   * Copy the verification code to the clipboard.
   */
  protected copyCode(): void {
    this.#clipboard.copy(this.smsModel().code);
    this.#notify.showSuccess('The verification code has been copied to the clipboard.');
  }

  /**
   * Close the dialog without sending an SMS.
   */
  protected onCancel(): void {
    this.#dialogRef.close(undefined);
  }

  /**
   * Send the SMS and close the dialog with the new internal note.
   */
  protected onSubmit(): void {
    if (this.isSubmitDisabled()) return;
    this.isSubmitting.set(true);
    this.sendError.set('');
    const { phone, code, text } = this.smsModel();
    this.#accessRequestService
      .sendVerificationSms(this.request.id, { phone, code, text })
      .subscribe({
        next: (note) => {
          this.#notify.showSuccess('The verification SMS has been sent.');
          this.#dialogRef.close(note);
        },
        error: (err: unknown) => {
          console.debug(err);
          const message =
            err instanceof HttpErrorResponse && err.status === 422
              ? 'The SMS could not be sent. Please check the phone number.'
              : 'The SMS could not be sent. Please try again later.';
          this.sendError.set(message);
          this.isSubmitting.set(false);
          this.#notify.showError(message);
        },
      });
  }
}
