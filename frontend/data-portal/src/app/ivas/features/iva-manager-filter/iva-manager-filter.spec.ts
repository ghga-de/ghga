/**
 * Test the IVA Manager Filter component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { IvaService } from '@app/ivas/services/iva';
import { IvaManagerFilter } from './iva-manager-filter';

import { provideNativeDateAdapter } from '@angular/material/core';
import { IvaState } from '@app/ivas/models/iva';
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
  setAllIvasFilter: vitest.fn(),
};

describe('IvaManagerFilter', () => {
  let component: IvaManagerFilter;
  let fixture: ComponentFixture<IvaManagerFilter>;
  let ivaService: IvaService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [IvaManagerFilter],
      providers: [
        { provide: IvaService, useValue: mockIvaService },
        provideNativeDateAdapter(),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(IvaManagerFilter);
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
    const textbox = screen.getByRole('textbox', { name: 'Name or email of user' });

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
    const combobox = screen.getByRole('combobox', { name: 'Status value' });

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

  it('should set the filter after typing modification dates', async () => {
    await userEvent.type(
      screen.getByRole('textbox', { name: 'Last modified from' }),
      '1/15/2025',
    );
    await userEvent.type(
      screen.getByRole('textbox', { name: 'Last modified until' }),
      '2/28/2025',
    );
    await fixture.whenStable();

    expect(mockIvaService.setAllIvasFilter).toHaveBeenLastCalledWith({
      name: '',
      fromDate: new Date(2025, 0, 15),
      toDate: new Date(2025, 1, 28),
      state: undefined,
    });
  });

  it('should clear the filter with the remove buttons', async () => {
    const name = screen.getByRole('textbox', { name: 'Name or email of user' });
    const until = screen.getByRole('textbox', { name: 'Last modified until' });
    await userEvent.type(name, 'Doe');
    await userEvent.type(until, '2/28/2025');
    await fixture.whenStable();

    await userEvent.click(
      screen.getByRole('button', { name: 'Remove filter for user name' }),
    );
    await userEvent.click(
      screen.getByRole('button', { name: 'Remove filter for dates ranging to' }),
    );
    await fixture.whenStable();

    const filter = mockIvaService.setAllIvasFilter.mock.lastCall![0];
    expect(filter.name).toBe('');
    expect(filter.toDate).toBeFalsy();
    expect(name).toHaveValue('');
    expect(until).toHaveValue('');
  });

  it('should show "All status values" under its label while no value is chosen', () => {
    expect(screen.getByRole('combobox', { name: 'Status value' })).toHaveTextContent(
      'All status values',
    );
  });
});
