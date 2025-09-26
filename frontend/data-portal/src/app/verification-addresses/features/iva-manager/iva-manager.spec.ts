/**
 * Test the IVA Manager component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { IvaManagerFilterComponent } from '../iva-manager-filter/iva-manager-filter';
import { IvaManagerListComponent } from '../iva-manager-list/iva-manager-list';
import { IvaManagerComponent } from './iva-manager';

import { IvaService } from '@app/verification-addresses/services/iva';

import { screen } from '@testing-library/angular';

/**
 * Mock the IVA service as needed by the IVA manager
 */
const mockIvaService = {
  loadAllIvas: jest.fn(),
};

describe('IvaManagerComponent', () => {
  let component: IvaManagerComponent;
  let fixture: ComponentFixture<IvaManagerComponent>;
  let ivaService: IvaService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [IvaManagerComponent],
      providers: [{ provide: IvaService, useValue: mockIvaService }],
    })
      .overrideComponent(IvaManagerComponent, {
        remove: { imports: [IvaManagerFilterComponent, IvaManagerListComponent] },
      })
      .compileComponents();

    fixture = TestBed.createComponent(IvaManagerComponent);
    ivaService = TestBed.inject(IvaService);
    component = fixture.componentInstance;
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
