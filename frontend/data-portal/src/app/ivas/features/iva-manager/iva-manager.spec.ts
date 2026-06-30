/**
 * Test the IVA Manager component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { IvaManagerComponent } from './iva-manager';

import { IvaService } from '@app/ivas/services/iva';

import { provideNativeDateAdapter } from '@angular/material/core';
import { ActivatedRoute } from '@angular/router';
import { allIvas } from '@app/../mocks/data';
import { fakeActivatedRoute } from '@app/../mocks/route';
import { screen } from '@testing-library/angular';

/**
 * Mock the IVA service as needed by the IVA manager
 */
class MockIvaService {
  allIvas = { value: () => allIvas, isLoading: () => false, error: () => undefined };
  allIvasFiltered = () => this.allIvas.value();
  allIvasFilter = () => ({
    name: '',
    fromDate: undefined,
    toDate: undefined,
    state: undefined,
  });
  setAllIvasFilter = () => undefined;
  loadAllIvas = vitest.fn();
  ambiguousUserIds = () => new Set<string>();
}

describe('IvaManagerComponent', () => {
  let component: IvaManagerComponent;
  let fixture: ComponentFixture<IvaManagerComponent>;
  let ivaService: IvaService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [IvaManagerComponent],
      providers: [
        { provide: IvaService, useClass: MockIvaService },
        { provide: ActivatedRoute, useValue: fakeActivatedRoute },
        provideNativeDateAdapter(),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(IvaManagerComponent);
    ivaService = TestBed.inject(IvaService);
    component = fixture.componentInstance;
    vitest.clearAllMocks();
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should show the proper heading', () => {
    const heading = screen.getByRole('heading', { level: 1 });
    expect(heading).toHaveTextContent('Independent Verification Address Management');
  });

  it('should load all the IVAs upon initialization', () => {
    expect(ivaService.loadAllIvas).toHaveBeenCalled();
  });
});
