/**
 * Test the IVA creation dialog component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MatDialogRef } from '@angular/material/dialog';
import { IvaType } from '@app/ivas/models/iva';
import { screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';
import { NewIvaDialogComponent } from './new-iva-dialog';

describe('NewIvaDialogComponent', () => {
  let component: NewIvaDialogComponent;
  let fixture: ComponentFixture<NewIvaDialogComponent>;
  const dialogRef = { close: vitest.fn() };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NewIvaDialogComponent],
      providers: [{ provide: MatDialogRef, useValue: dialogRef }],
    }).compileComponents();

    fixture = TestBed.createComponent(NewIvaDialogComponent);
    component = fixture.componentInstance;
    dialogRef.close.mockClear();
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should submit an in-person IVA with the entered location', async () => {
    const submit = screen.getByRole('button', { name: 'Submit' });
    expect(submit).toBeDisabled();

    await userEvent.click(screen.getByRole('radio', { name: 'In Person' }));
    await fixture.whenStable();
    expect(submit).toBeDisabled();

    await userEvent.type(screen.getByRole('textbox'), ' Mathematikon ');
    await fixture.whenStable();
    expect(submit).toBeEnabled();

    await userEvent.click(submit);
    expect(dialogRef.close).toHaveBeenCalledWith({
      type: IvaType.InPerson,
      value: 'Mathematikon',
    });
  });

  it('should submit an SMS IVA with the entered phone number', async () => {
    await userEvent.click(screen.getByRole('radio', { name: 'SMS' }));
    await fixture.whenStable();

    await userEvent.type(screen.getByRole('textbox'), '1701234567');
    await fixture.whenStable();

    const submit = screen.getByRole('button', { name: 'Submit' });
    expect(submit).toBeEnabled();
    await userEvent.click(submit);
    expect(dialogRef.close).toHaveBeenCalledWith({
      type: IvaType.Phone,
      value: '+491701234567',
    });
  });

  it('should not submit an empty value', async () => {
    await userEvent.click(screen.getByRole('radio', { name: 'In Person' }));
    await userEvent.type(screen.getByRole('textbox'), '   ');
    await fixture.whenStable();
    await userEvent.click(screen.getByRole('button', { name: 'Submit' }));
    expect(dialogRef.close).not.toHaveBeenCalled();
  });
});
