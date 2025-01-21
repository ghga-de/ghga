/**
 * Test the custom snackbar
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MAT_SNACK_BAR_DATA, MatSnackBarRef } from '@angular/material/snack-bar';
import { CustomSnackBarComponent } from './custom-snack-bar.component';

describe('CustomSnackBarComponent', () => {
  let component: CustomSnackBarComponent;
  let fixture: ComponentFixture<CustomSnackBarComponent>;

  beforeEach(async () => {
    const matSnackBarData = { message: 'Test message', type: 'ok' };
    const mockMatSnackBarRef = { dismiss: jest.fn() };
    await TestBed.configureTestingModule({
      imports: [CustomSnackBarComponent],
      providers: [
        { provide: MAT_SNACK_BAR_DATA, useValue: matSnackBarData },
        { provide: MatSnackBarRef, useValue: mockMatSnackBarRef },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(CustomSnackBarComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
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
    const span = fixture.nativeElement.querySelector('span');
    expect(span).toBeTruthy();
    expect(span.textContent).toContain('Test message');
  });

  it('should close the snackbar when close button is clicked', () => {
    const button = fixture.nativeElement.querySelector('button');
    expect(button).toBeTruthy();
    button.click();
    expect(component.snackBarRef.dismiss).toHaveBeenCalled();
  });
});
