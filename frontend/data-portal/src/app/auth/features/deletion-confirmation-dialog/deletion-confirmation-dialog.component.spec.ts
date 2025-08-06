/**
 * Tests for the deletion confirmation dialog
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { users } from '@app/../mocks/data';
import { screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';
import { DeletionConfirmationDialogComponent } from './deletion-confirmation-dialog.component';

describe('DeletionConfirmationDialogComponent', () => {
  let component: DeletionConfirmationDialogComponent;
  let fixture: ComponentFixture<DeletionConfirmationDialogComponent>;

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
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DeletionConfirmationDialogComponent);
    component = fixture.componentInstance;
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

  it('should return true when confirmed after confirming the user email', async () => {
    const input = screen.getByRole('textbox');
    await userEvent.type(input, 'doe@home.org');
    jest.spyOn(dialogRef, 'close');
    expect(dialogRef.close).not.toHaveBeenCalled();
    const button = screen.getByRole('button', { name: 'Confirm deletion' });
    expect(button).toBeVisible();
    expect(button).toHaveTextContent('Confirm deletion');
    button.click();
    expect(dialogRef.close).toHaveBeenCalledWith(true);
  });
});
