/**
 * Test the verification code creation dialog
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';

import { screen } from '@testing-library/angular';

import { allIvasOfDoe } from '@app/../mocks/data';
import { CodeCreationDialogComponent } from './code-creation-dialog';

const TEST_IVA = { ...allIvasOfDoe[0], code: 'ABC123' };

describe('CodeCreationDialogComponent', () => {
  let component: CodeCreationDialogComponent;
  let fixture: ComponentFixture<CodeCreationDialogComponent>;

  const dialogRef = {
    close: jest.fn(),
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CodeCreationDialogComponent],
      providers: [
        { provide: MAT_DIALOG_DATA, useValue: TEST_IVA },
        { provide: MatDialogRef, useValue: dialogRef },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(CodeCreationDialogComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should display the proper heading', () => {
    const heading = screen.getByRole('heading', { level: 1 });
    expect(heading).toHaveTextContent('Verification code created');
  });

  it('should display the name of the user', () => {
    const compiled = fixture.nativeElement;
    const content = compiled.querySelector('.mat-mdc-dialog-content');
    expect(content).toBeTruthy();
    expect(content.textContent).toContain('Dr. John Doe');
  });

  it('should display the email of the user', () => {
    const compiled = fixture.nativeElement;
    const content = compiled.querySelector('.mat-mdc-dialog-content');
    expect(content).toBeTruthy();
    expect(content.textContent).toContain('doe@home.org');
  });

  it('should display the IVA type', () => {
    const compiled = fixture.nativeElement;
    const content = compiled.querySelector('.mat-mdc-dialog-content');
    expect(content).toBeTruthy();
    expect(content.textContent).toContain('SMS');
  });

  it('should display the IVA value', () => {
    const compiled = fixture.nativeElement;
    const content = compiled.querySelector('.mat-mdc-dialog-content');
    expect(content).toBeTruthy();
    expect(content.textContent).toContain('+491234567890000');
  });

  it('should display the verification code in an input field', () => {
    const compiled = fixture.nativeElement;
    const input = compiled.querySelector('.mat-mdc-dialog-content input');
    expect(input).toBeTruthy();
    expect(input.value).toBe('ABC123');
  });

  it('should return false when closed', () => {
    jest.spyOn(dialogRef, 'close');
    expect(dialogRef.close).not.toHaveBeenCalled();
    // Workaround for jest selector validation issue
    // const button = screen.getByRole('button', { name: 'Close and send later' });
    const button = screen.getByText('Close and send later');
    expect(button).toBeVisible();
    button.click();
    expect(dialogRef.close).toHaveBeenCalledWith(false);
  });

  it('should return true when transmission confirmed', () => {
    jest.spyOn(dialogRef, 'close');
    expect(dialogRef.close).not.toHaveBeenCalled();
    // Workaround for jest selector validation issue
    //const button = screen.getByRole('button', { name: 'Confirm transmission' });
    const button = screen.getByText('Confirm transmission');
    expect(button).toBeVisible();
    button.click();
    expect(dialogRef.close).toHaveBeenCalledWith(true);
  });
});
