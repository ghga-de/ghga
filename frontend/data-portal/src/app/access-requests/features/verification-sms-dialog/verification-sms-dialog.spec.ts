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
import { of, throwError } from 'rxjs';

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
    await userEvent.type(phone, '6221424242');
    await userEvent.clear(text);
    await userEvent.type(text, 'No code here');
    await fixture.whenStable();
    expect(screen.getByRole('button', { name: 'Send SMS' })).toBeDisabled();
  });

  it('should send the SMS with a German number and close with the new note', async () => {
    accessRequestService.sendVerificationSms.mockReturnValue(of('the note'));
    const { phone, code, text } = fields();
    await userEvent.type(phone, '6221424242');
    await fixture.whenStable();
    await userEvent.click(screen.getByRole('button', { name: 'Send SMS' }));

    expect(accessRequestService.sendVerificationSms).toHaveBeenCalledWith(
      TEST_REQUEST.id,
      { phone: '+496221424242', code: code.value, text: text.value },
    );
    expect(dialogRef.close).toHaveBeenCalledWith('the note');
  });

  it('should show an error and stay open if the SMS cannot be sent', async () => {
    accessRequestService.sendVerificationSms.mockReturnValue(
      throwError(() => new HttpErrorResponse({ status: 422 })),
    );
    await userEvent.type(fields().phone, '6221424242');
    await fixture.whenStable();
    await userEvent.click(screen.getByRole('button', { name: 'Send SMS' }));
    await fixture.whenStable();

    expect(screen.getByRole('alert')).toHaveTextContent(/check the phone number/);
    expect(dialogRef.close).not.toHaveBeenCalled();
  });
});
