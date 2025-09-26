/**
 * Test the IVA verification dialog component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { VerificationDialogComponent } from './verification-dialog';

describe('VerificationDialogComponent', () => {
  let component: VerificationDialogComponent;
  let fixture: ComponentFixture<VerificationDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [VerificationDialogComponent, NoopAnimationsModule],
      providers: [
        { provide: MAT_DIALOG_DATA, useValue: { address: 'SMS: 123/456' } },
        { provide: MatDialogRef, useValue: {} },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(VerificationDialogComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
