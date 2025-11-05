/**
 * Tests for the deletion confirmation dialog
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { provideHttpClient } from '@angular/common/http';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { users } from '@app/../mocks/data';
import { UserService } from '@app/auth/services/user';
import { ConfigService } from '@app/shared/services/config';
import { screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';
import { DeletionConfirmationDialogComponent } from './deletion-confirmation-dialog';

const MockConfigService = {
  auth_url: '/test/auth',
};
const MockUserService = {
  deleteUser: jest.fn(),
};

describe('DeletionConfirmationDialogComponent', () => {
  let component: DeletionConfirmationDialogComponent;
  let fixture: ComponentFixture<DeletionConfirmationDialogComponent>;
  let service: UserService;

  const dialogRef = {
    close: jest.fn(),
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DeletionConfirmationDialogComponent],
      providers: [
        {
          provide: MAT_DIALOG_DATA,
          useValue: {
            user: users[0],
          },
        },
        { provide: MatDialogRef, useValue: dialogRef },
        { provide: UserService, useValue: MockUserService },
        { provide: ConfigService, useValue: MockConfigService },
        provideHttpClient(),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DeletionConfirmationDialogComponent);
    component = fixture.componentInstance;
    service = fixture.debugElement.injector.get(UserService);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should return false when cancelled', () => {
    jest.spyOn(dialogRef, 'close');
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
    const deleteSpy = jest.spyOn(service, 'deleteUser');
    expect(deleteSpy).not.toHaveBeenCalled();
    const button = screen.getByRole('button', { name: 'Confirm deletion' });
    expect(button).toBeEnabled();
    expect(button).toHaveTextContent('Confirm deletion');
    button.click();
    expect(deleteSpy).toHaveBeenCalledWith(users[0].id);
  });
});
