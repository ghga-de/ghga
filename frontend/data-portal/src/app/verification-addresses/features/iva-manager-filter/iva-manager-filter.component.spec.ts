/**
 * Test the IVA Manager Filter component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { IvaService } from '@app/verification-addresses/services/iva.service';
import { IvaManagerFilterComponent } from './iva-manager-filter.component';

import { provideNativeDateAdapter } from '@angular/material/core';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { IvaState } from '@app/verification-addresses/models/iva';
import { screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';

/**
 * Mock the IVA service as needed by the IVA manager filter component
 */
const mockIvaService = {
  allIvasFilter: () => ({
    name: '',
    fromDate: undefined,
    toDate: undefined,
    state: undefined,
  }),
  setAllIvasFilter: jest.fn(),
};

describe('IvaManagerFilterComponent', () => {
  let component: IvaManagerFilterComponent;
  let fixture: ComponentFixture<IvaManagerFilterComponent>;
  let ivaService: IvaService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [IvaManagerFilterComponent],
      providers: [
        { provide: IvaService, useValue: mockIvaService },
        provideNativeDateAdapter(),
        provideNoopAnimations(),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(IvaManagerFilterComponent);
    component = fixture.componentInstance;
    ivaService = TestBed.inject(IvaService);
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should reset the filter upon initialization', async () => {
    expect(ivaService.setAllIvasFilter).toHaveBeenCalledWith({
      name: '',
      fromDate: undefined,
      toDate: undefined,
      state: undefined,
    });
  });

  it('should set the filter after typing a name', async () => {
    const textbox = screen.getByRole('textbox', { name: 'User name' });

    await userEvent.type(textbox, 'Doe');
    await fixture.whenStable();

    expect(ivaService.setAllIvasFilter).toHaveBeenCalledWith({
      name: 'Doe',
      fromDate: undefined,
      toDate: undefined,
      state: undefined,
    });
  });

  it('should set the filter after selecting a state', async () => {
    const combobox = screen.getByRole('combobox', { name: 'All status values' });

    await userEvent.click(combobox);
    await fixture.whenStable();

    const option = screen.getByRole('option', { name: 'Code Requested' });
    await userEvent.click(option);
    await fixture.whenStable();

    expect(ivaService.setAllIvasFilter).toHaveBeenCalledWith({
      name: '',
      fromDate: undefined,
      toDate: undefined,
      state: IvaState.CodeRequested,
    });
  });
});
