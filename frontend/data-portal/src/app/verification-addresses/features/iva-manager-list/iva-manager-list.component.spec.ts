/**
 * Test the IVA Manager List component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { allIvas } from '@app/../mocks/data';
import { IvaService } from '@app/verification-addresses/services/iva.service';
import { IvaManagerListComponent } from './iva-manager-list.component';

/**
 * Mock the IVA service as needed by the IVA Manager list component
 */
class MockIvaService {
  allIvas = { value: () => allIvas, isLoading: () => false, error: () => undefined };
  allIvasFiltered = () => this.allIvas.value();
}

describe('IvaManagerListComponent', () => {
  let component: IvaManagerListComponent;
  let fixture: ComponentFixture<IvaManagerListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [IvaManagerListComponent],
      providers: [{ provide: IvaService, useClass: MockIvaService }],
    }).compileComponents();

    fixture = TestBed.createComponent(IvaManagerListComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should show IVA values', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const text = compiled.textContent;
    expect(text).toContain('+441234567890004');
    expect(text).toContain('Wilhelmstr. 123');
  });
});
