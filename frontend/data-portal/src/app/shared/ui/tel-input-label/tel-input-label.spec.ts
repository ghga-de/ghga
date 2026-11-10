/**
 * Test the directive that names the phone input of ngx-mat-input-tel
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { MatFormFieldModule } from '@angular/material/form-field';
import { screen } from '@testing-library/angular';
import { NgxMatInputTelComponent } from 'ngx-mat-input-tel';
import { TelInputLabel } from './tel-input-label';

/**
 * Host with a phone input in a form field with a label
 */
@Component({
  imports: [MatFormFieldModule, NgxMatInputTelComponent, TelInputLabel],
  template: `<mat-form-field>
    <mat-label>Phone number</mat-label>
    <ngx-mat-input-tel appTelInputLabel ariaLabel="Select country"></ngx-mat-input-tel>
  </mat-form-field>`,
})
class LabelledHost {}

/**
 * Host with a phone input in a form field without a label
 */
@Component({
  imports: [MatFormFieldModule, NgxMatInputTelComponent, TelInputLabel],
  template: `<mat-form-field>
    <ngx-mat-input-tel appTelInputLabel="Your phone"></ngx-mat-input-tel>
  </mat-form-field>`,
})
class UnlabelledHost {}

describe('TelInputLabel', () => {
  it('should name the phone input by the label of the form field', async () => {
    const fixture = TestBed.createComponent(LabelledHost);
    await fixture.whenStable();
    expect(screen.getByRole('textbox', { name: 'Phone number' })).toHaveAttribute(
      'type',
      'tel',
    );
    // the country selector keeps its own name
    expect(screen.getByRole('button', { name: 'Select country' })).toBeTruthy();
  });

  it('should name the phone input by the given text without a label', async () => {
    const fixture = TestBed.createComponent(UnlabelledHost);
    await fixture.whenStable();
    expect(screen.getByRole('textbox', { name: 'Your phone' })).toHaveAttribute(
      'type',
      'tel',
    );
  });
});
