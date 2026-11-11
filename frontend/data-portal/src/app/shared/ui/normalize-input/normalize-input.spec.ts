/**
 * Test the normalize input directive
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component } from '@angular/core';
import { fireEvent, render, screen } from '@testing-library/angular';
import { NormalizeInput } from './normalize-input';

const toDigits = (value: string): string => value.replace(/\D/g, '').slice(0, 6);

/**
 * Host component with a normalized input
 */
@Component({
  imports: [NormalizeInput],
  template: `<input aria-label="Code" [appNormalize]="toDigits" />`,
})
class TestHost {
  protected toDigits = toDigits;
}

/**
 * Render the host and return its input
 * @returns the input element
 */
async function renderInput(): Promise<HTMLInputElement> {
  await render(TestHost);
  return screen.getByRole<HTMLInputElement>('textbox', { name: 'Code' });
}

describe('NormalizeInput', () => {
  it('should remove a rejected character that leaves the value unchanged', async () => {
    const input = await renderInput();
    fireEvent.input(input, { target: { value: '123' } });
    fireEvent.input(input, { target: { value: '123a' } });
    expect(input).toHaveValue('123');
  });

  it('should normalize pasted text', async () => {
    const input = await renderInput();
    fireEvent.input(input, { target: { value: '123 456 789' } });
    expect(input).toHaveValue('123456');
  });

  it('should keep the caret after the kept characters before it', async () => {
    const input = await renderInput();
    input.focus();
    input.value = '12x34';
    input.setSelectionRange(3, 3);
    fireEvent.input(input);
    expect(input).toHaveValue('1234');
    expect(input.selectionStart).toBe(2);
  });

  it('should leave a value that is already normalized alone', async () => {
    const input = await renderInput();
    input.focus();
    input.value = '1234';
    input.setSelectionRange(1, 1);
    fireEvent.input(input);
    expect(input).toHaveValue('1234');
    expect(input.selectionStart).toBe(1);
  });
});
