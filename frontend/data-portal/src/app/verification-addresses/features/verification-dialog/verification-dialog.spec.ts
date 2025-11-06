/**
 * Test the IVA verification dialog component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { IvaService } from '@app/verification-addresses/services/iva';
import { VerificationDialogComponent } from './verification-dialog';

describe('VerificationDialogComponent', () => {
  let component: VerificationDialogComponent;
  let fixture: ComponentFixture<VerificationDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [VerificationDialogComponent],
      providers: [
        { provide: MAT_DIALOG_DATA, useValue: { address: 'SMS: 123/456' } },
        { provide: IvaService, useValue: {} },
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
