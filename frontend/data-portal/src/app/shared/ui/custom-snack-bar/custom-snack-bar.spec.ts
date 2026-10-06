/**
 * Test the custom snackbar
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { render, RenderResult, screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';

import { MAT_SNACK_BAR_DATA, MatSnackBarRef } from '@angular/material/snack-bar';
import { CustomSnackBar } from './custom-snack-bar';

describe('CustomSnackBar', () => {
  let result: RenderResult<CustomSnackBar>;
  let component: CustomSnackBar;

  beforeEach(async () => {
    const matSnackBarData = { message: 'Test message', type: 'ok' };
    const mockMatSnackBarRef = { dismiss: vitest.fn() };
    result = await render(CustomSnackBar, {
      providers: [
        { provide: MAT_SNACK_BAR_DATA, useValue: matSnackBarData },
        { provide: MatSnackBarRef, useValue: mockMatSnackBarRef },
      ],
    });
    component = result.fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should have the snack bar data set property', () => {
    const data = component.data;
    expect(data).toBeTruthy();
    expect(data.type).toBe('ok');
    expect(data.message).toBe('Test message');
  });

  it('should show the message', () => {
    const message = screen.getByText('Test message');
    expect(message).toBeTruthy();
    expect(message).toHaveTextContent(/^Test message$/);
  });

  it('should close the snackbar when close button is clicked', async () => {
    const button = screen.getByRole('button', { name: 'Close' });
    expect(button).toBeTruthy();
    await userEvent.click(button);
    expect(component.snackBarRef.dismiss).toHaveBeenCalled();
  });
});
