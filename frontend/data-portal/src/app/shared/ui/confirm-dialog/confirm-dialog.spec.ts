/**
 * Test the confirm dialog component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { screen } from '@testing-library/angular';

import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { Html } from '@app/shared/utils/html';
import { ConfirmDialog, ConfirmDialogData } from './confirm-dialog';

// the html tag only escapes values, so this markup is wrapped directly
const UNSAFE_MESSAGE = new Html(
  '<strong>Test<script>alert("Security Risk")</script> message</strong>',
);

describe('ConfirmDialog', () => {
  let component: ConfirmDialog;
  let fixture: ComponentFixture<ConfirmDialog>;

  const dialogRef = {
    close: vitest.fn(),
  };

  /**
   * Create the dialog for the given data
   * @param data - the data passed to the dialog
   */
  async function createDialog(data: ConfirmDialogData): Promise<void> {
    await TestBed.configureTestingModule({
      imports: [ConfirmDialog],
      providers: [
        { provide: MAT_DIALOG_DATA, useValue: data },
        { provide: MatDialogRef, useValue: dialogRef },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ConfirmDialog);
    component = fixture.componentInstance;
    vitest.clearAllMocks();
    await fixture.whenStable();
  }

  /**
   * Get the rendered dialog content
   * @returns the element holding the message
   */
  function getContent(): HTMLElement {
    return fixture.nativeElement.querySelector('.mat-mdc-dialog-content');
  }

  describe('with an HTML message', () => {
    beforeEach(async () => {
      await createDialog({ message: UNSAFE_MESSAGE });
    });

    it('should create', () => {
      expect(component).toBeTruthy();
    });

    it('should display the test message', () => {
      expect(getContent().textContent).toBe('Test message');
    });

    it('should only render text and safe HTML tags', () => {
      expect(getContent().innerHTML).toBe('<strong>Test message</strong>');
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

  describe('with a plain string message', () => {
    beforeEach(async () => {
      await createDialog({ message: '<strong>Test</strong> & message' });
    });

    it('should render the message as text', () => {
      expect(getContent().textContent).toBe('<strong>Test</strong> & message');
    });
  });
});
