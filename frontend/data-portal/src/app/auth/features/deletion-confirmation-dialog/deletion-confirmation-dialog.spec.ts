/**
 * Tests for the deletion confirmation dialog
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { provideHttpClient } from '@angular/common/http';
import { provideHttpCache } from '@ngneat/cashew';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { users } from '@app/../mocks/data';
import { UserService } from '@app/auth/services/user';
import { ConfigService } from '@app/shared/services/config';
import { Notifier } from '@app/shared/services/notification';
import { screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';
import { of } from 'rxjs';
import { DeletionConfirmationDialog } from './deletion-confirmation-dialog';

const MockConfigService = {
  auth_url: '/test/auth',
};
const MockUserService = {
  deleteUser: vitest.fn(() => of(null)),
};

// A real notifier opens snack bars in document.body, which the test runner
// shares between spec files.
const MockNotifier = {
  showSuccess: vitest.fn(),
  showError: vitest.fn(),
};

describe('DeletionConfirmationDialog', () => {
  let component: DeletionConfirmationDialog;
  let fixture: ComponentFixture<DeletionConfirmationDialog>;
  let service: UserService;

  const dialogRef = {
    close: vitest.fn(),
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DeletionConfirmationDialog],
      providers: [
        { provide: MAT_DIALOG_DATA, useValue: { user: users[0] } },
        { provide: MatDialogRef, useValue: dialogRef },
        { provide: UserService, useValue: MockUserService },
        { provide: ConfigService, useValue: MockConfigService },
        { provide: Notifier, useValue: MockNotifier },
        provideHttpClient(),
        provideHttpCache(),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DeletionConfirmationDialog);
    component = fixture.componentInstance;
    // The opener's instance, so its local updates reach the user list
    service = TestBed.inject(UserService);
    vitest.clearAllMocks();
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should return false when cancelled', () => {
    expect(dialogRef.close).not.toHaveBeenCalled();
    const button = screen.getByRole('button', { name: 'Cancel' });
    expect(button).toBeVisible();
    expect(button).toHaveTextContent('Cancel');
    button.click();
    expect(dialogRef.close).toHaveBeenCalledWith(false);
  });

  it('should call the delete user method when confirmed after confirming the user email', async () => {
    const input = screen.getByRole('textbox');
    await userEvent.type(input, 'doe@home.org');
    const deleteSpy = vitest.spyOn(service, 'deleteUser');
    expect(deleteSpy).not.toHaveBeenCalled();
    const button = screen.getByRole('button', { name: 'Confirm deletion' });
    expect(button).toBeEnabled();
    expect(button).toHaveTextContent('Confirm deletion');
    button.click();
    expect(deleteSpy).toHaveBeenCalledWith(users[0].id);
    expect(MockNotifier.showSuccess).toHaveBeenCalled();
    expect(dialogRef.close).toHaveBeenCalledWith(true);
  });

  it('should keep the confirm button disabled until the email matches', async () => {
    const button = screen.getByRole('button', { name: 'Confirm deletion' });
    expect(button).toBeDisabled();
    const input = screen.getByRole('textbox', { name: 'Confirm user email' });
    await userEvent.type(input, 'doe@home.or');
    expect(button).toBeDisabled();
    await userEvent.clear(input);
    await userEvent.type(input, ' doe@home.org ');
    expect(button).toBeEnabled();
  });
});
