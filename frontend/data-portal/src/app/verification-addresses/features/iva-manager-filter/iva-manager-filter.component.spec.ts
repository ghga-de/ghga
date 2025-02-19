/**
 * Test the IVA Manager Filter component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { IvaManagerFilterComponent } from './iva-manager-filter.component';

describe('IvaManagerFilterComponent', () => {
  let component: IvaManagerFilterComponent;
  let fixture: ComponentFixture<IvaManagerFilterComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [IvaManagerFilterComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(IvaManagerFilterComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
