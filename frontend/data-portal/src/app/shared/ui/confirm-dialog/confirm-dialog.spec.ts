/**
 * Test the confirm dialog component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { screen } from '@testing-library/angular';

import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { ConfirmDialogComponent } from './confirm-dialog';

describe('ConfirmDialogComponent', () => {
  let component: ConfirmDialogComponent;
  let fixture: ComponentFixture<ConfirmDialogComponent>;

  const dialogRef = {
    close: vitest.fn(),
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConfirmDialogComponent],
      providers: [
        {
          provide: MAT_DIALOG_DATA,
          useValue: {
            message:
              '<strong>Test<script>alert("Security Risk")</script> message</strong>',
          },
        },
        { provide: MatDialogRef, useValue: dialogRef },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ConfirmDialogComponent);
    component = fixture.componentInstance;
    vitest.clearAllMocks();
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should display the test message', () => {
    const compiled = fixture.nativeElement;
    const content = compiled.querySelector('.mat-mdc-dialog-content');
    expect(content).toBeTruthy();
    expect(content.textContent).toBe('Test message');
  });

  it('should only render text and safe HTML tags', () => {
    const compiled = fixture.nativeElement;
    const content = compiled.querySelector('.mat-mdc-dialog-content');
    expect(content).toBeTruthy();
    const html = content.innerHTML;
    expect(html).toBe('<strong>Test message</strong>');
  });

  it('should return false when cancelled', () => {
    expect(dialogRef.close).not.toHaveBeenCalled();
    const button = screen.getByRole('button', { name: 'Cancel' });
    expect(button).toBeVisible();
    expect(button).toHaveTextContent('Cancel');
    button.click();
    expect(dialogRef.close).toHaveBeenCalledWith(false);
  });

  it('should return true when confirmed', () => {
    expect(dialogRef.close).not.toHaveBeenCalled();
    const button = screen.getByRole('button', { name: 'Continue' });
    expect(button).toBeVisible();
    expect(button).toHaveTextContent('Continue');
    button.click();
    expect(dialogRef.close).toHaveBeenCalledWith(true);
  });
});
