/**
 * Unit tests for the dialog to revoke access grants
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { accessGrants } from '@app/../mocks/data';
import { screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';
import { AccessGrantRevocationDialogComponent } from './access-grant-revocation-dialog';

describe('AccessGrantRevocationDialogComponent', () => {
  let component: AccessGrantRevocationDialogComponent;
  let fixture: ComponentFixture<AccessGrantRevocationDialogComponent>;

  const dialogRef = {
    close: jest.fn(),
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AccessGrantRevocationDialogComponent],
      providers: [
        {
          provide: MAT_DIALOG_DATA,
          useValue: {
            grant: accessGrants[0],
          },
        },
        { provide: MatDialogRef, useValue: dialogRef },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AccessGrantRevocationDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    jest.clearAllMocks();
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

  it('should return true when confirmed after confirming the user and dataset', async () => {
    const nameInput = screen.getByPlaceholderText('Confirm email of user');
    await userEvent.type(nameInput, 'doe@home.org');
    const datasetInput = screen.getByPlaceholderText('Confirm dataset accession');
    await userEvent.type(datasetInput, 'GHGAD12345678901234');
    jest.spyOn(dialogRef, 'close');
    expect(dialogRef.close).not.toHaveBeenCalled();
    const button = screen.getByRole('button', { name: 'Confirm revocation' });
    expect(button).toBeVisible();
    expect(button).toHaveTextContent('Confirm revocation');
    button.click();
    expect(dialogRef.close).toHaveBeenCalledWith(true);
  });
});
