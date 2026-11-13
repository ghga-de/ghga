/**
 * Test the dialog for sending a verification SMS to the DAC
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpErrorResponse } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { AccessRequest } from '@app/access-requests/models/access-requests';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';
import { NEVER, of, throwError } from 'rxjs';

import { accessRequests } from '@app/../mocks/data';
import { VerificationSmsDialog, verificationSmsText } from './verification-sms-dialog';

const TEST_REQUEST = {
  ...accessRequests[4],
  ticket_id: 'T-1234',
} as AccessRequest;

const dialogRef = { close: vitest.fn() };
const accessRequestService = { sendVerificationSms: vitest.fn() };

let fixture: ComponentFixture<VerificationSmsDialog>;

/**
 * Get the input fields of the dialog.
 * @returns the phone, code and message inputs
 */
function fields() {
  return {
    phone: screen.getByRole('textbox', { name: 'Phone number' }) as HTMLInputElement,
    code: screen.getByLabelText('Verification code') as HTMLInputElement,
    text: screen.getByLabelText('Message') as HTMLTextAreaElement,
  };
}

describe('VerificationSmsDialog', () => {
  beforeEach(async () => {
    vitest.clearAllMocks();
    await TestBed.configureTestingModule({
      imports: [VerificationSmsDialog],
      providers: [
        { provide: MAT_DIALOG_DATA, useValue: TEST_REQUEST },
        { provide: MatDialogRef, useValue: dialogRef },
        { provide: AccessRequestService, useValue: accessRequestService },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(VerificationSmsDialog);
    await fixture.whenStable();
  });

  it('should prefill a generated code and the message containing it', () => {
    const { code, text } = fields();
    expect(code.value).toMatch(/^[2-9A-HJ-NP-Z]{6}$/);
    expect(text.value).toBe(verificationSmsText(TEST_REQUEST, code.value));
    expect(text.value).toContain(TEST_REQUEST.full_user_name);
    expect(text.value).toContain(TEST_REQUEST.dataset_id);
    expect(text.value).toContain('quoting ticket T-1234');
  });

  it('should let the message follow a changed code', async () => {
    const { code, text } = fields();
    await userEvent.clear(code);
    await userEvent.type(code, 'MYCODE');
    await fixture.whenStable();
    expect(text.value).toBe(verificationSmsText(TEST_REQUEST, 'MYCODE'));
  });

  it('should keep a message that was edited by hand', async () => {
    const { code, text } = fields();
    await userEvent.clear(text);
    await userEvent.type(text, 'Please send MYCODE');
    await userEvent.clear(code);
    await userEvent.type(code, 'MYCODE');
    await fixture.whenStable();
    expect(text.value).toBe('Please send MYCODE');
  });

  it('should not send without a phone number', () => {
    const send = screen.getByRole('button', { name: 'Send SMS' });
    expect(send).toBeDisabled();
  });

  it('should not send a message that misses the code', async () => {
    const { phone, text } = fields();
    await userEvent.type(phone, '15123456789');
    await userEvent.clear(text);
    await userEvent.type(text, 'No code here');
    await fixture.whenStable();
    expect(screen.getByRole('button', { name: 'Send SMS' })).toBeDisabled();
  });

  it('should send the SMS with a German mobile number and close with the new note', async () => {
    accessRequestService.sendVerificationSms.mockReturnValue(of('the note'));
    const { phone, code, text } = fields();
    await userEvent.type(phone, '15123456789');
    await fixture.whenStable();
    await userEvent.click(screen.getByRole('button', { name: 'Send SMS' }));

    expect(accessRequestService.sendVerificationSms).toHaveBeenCalledWith(
      TEST_REQUEST.id,
      { phone: '+4915123456789', code: code.value, text: text.value },
    );
    expect(dialogRef.close).toHaveBeenCalledWith('the note');
  });

  it('should show an error and stay open if the SMS cannot be sent', async () => {
    accessRequestService.sendVerificationSms.mockReturnValue(
      throwError(() => new HttpErrorResponse({ status: 422 })),
    );
    await userEvent.type(fields().phone, '15123456789');
    await fixture.whenStable();
    await userEvent.click(screen.getByRole('button', { name: 'Send SMS' }));
    await fixture.whenStable();

    expect(screen.getByRole('alert')).toHaveTextContent(/check the phone number/);
    expect(dialogRef.close).not.toHaveBeenCalled();
  });

  it('should show the reason if the backend refuses to send the SMS', async () => {
    const detail = 'Access request has already been processed';
    accessRequestService.sendVerificationSms.mockReturnValue(
      throwError(() => new HttpErrorResponse({ status: 422, error: { detail } })),
    );
    await userEvent.type(fields().phone, '15123456789');
    await fixture.whenStable();
    await userEvent.click(screen.getByRole('button', { name: 'Send SMS' }));
    await fixture.whenStable();

    expect(screen.getByRole('alert')).toHaveTextContent(`could not be sent: ${detail}`);
    expect(dialogRef.close).not.toHaveBeenCalled();
  });

  it('should ask to try again later after a server error', async () => {
    accessRequestService.sendVerificationSms.mockReturnValue(
      throwError(() => new HttpErrorResponse({ status: 500 })),
    );
    await userEvent.type(fields().phone, '15123456789');
    await fixture.whenStable();
    await userEvent.click(screen.getByRole('button', { name: 'Send SMS' }));
    await fixture.whenStable();

    expect(screen.getByRole('alert')).toHaveTextContent(/try again later/);
    expect(dialogRef.close).not.toHaveBeenCalled();
  });

  it('should not let the dialog be cancelled while the SMS is being sent', async () => {
    accessRequestService.sendVerificationSms.mockReturnValue(NEVER);
    const cancel = screen.getByRole('button', { name: 'Cancel' });
    expect(cancel).toBeEnabled();
    await userEvent.type(fields().phone, '15123456789');
    await fixture.whenStable();
    await userEvent.click(screen.getByRole('button', { name: 'Send SMS' }));
    await fixture.whenStable();

    expect(cancel).toBeDisabled();
  });

  it('should close without a note when cancelled after a refusal', async () => {
    accessRequestService.sendVerificationSms.mockReturnValue(
      throwError(() => new HttpErrorResponse({ status: 422 })),
    );
    await userEvent.type(fields().phone, '15123456789');
    await fixture.whenStable();
    await userEvent.click(screen.getByRole('button', { name: 'Send SMS' }));
    await fixture.whenStable();
    await userEvent.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(dialogRef.close).toHaveBeenCalledWith(undefined);
  });

  it('should close with null when cancelled after a server error', async () => {
    accessRequestService.sendVerificationSms.mockReturnValue(
      throwError(() => new HttpErrorResponse({ status: 500 })),
    );
    await userEvent.type(fields().phone, '15123456789');
    await fixture.whenStable();
    await userEvent.click(screen.getByRole('button', { name: 'Send SMS' }));
    await fixture.whenStable();
    await userEvent.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(dialogRef.close).toHaveBeenCalledWith(null);
  });
});
