/**
 * Test the IVA Manager List component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ActivatedRoute } from '@angular/router';
import { allIvas } from '@app/../mocks/data';
import { fakeActivatedRoute } from '@app/../mocks/route';
import { IvaService } from '@app/ivas/services/iva';
import { IvaManagerListComponent } from './iva-manager-list';

/**
 * Mock the IVA service as needed by the IVA Manager list component
 */
class MockIvaService {
  allIvas = { value: () => allIvas, isLoading: () => false, error: () => undefined };
  allIvasFiltered = () => this.allIvas.value();
  ambiguousUserIds = () => new Set<string>();
}

describe('IvaManagerListComponent', () => {
  let component: IvaManagerListComponent;
  let fixture: ComponentFixture<IvaManagerListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [IvaManagerListComponent],
      providers: [
        { provide: IvaService, useClass: MockIvaService },
        { provide: ActivatedRoute, useValue: fakeActivatedRoute },
      ],
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
    expect(text).toContain(
      'c/o Weird Al Yankovic, Dr. John Doe, Wilhelmstraße 123, Apartment 25, Floor 2, 72072 Tübingen, Baden-Württemberg, Deutschland',
    );
  });
});
