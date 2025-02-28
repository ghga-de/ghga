/**
 * Test the Access Request Manager Filter component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { provideNativeDateAdapter } from '@angular/material/core';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { AccessRequestService } from '@app/access-requests/services/access-request.service';
import { AccessRequestManagerFilterComponent } from './access-request-manager-filter.component';

import { AccessRequestStatus } from '@app/access-requests/models/access-requests';
import { screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';

/**
 * Mock the access request service as needed by the access request manager filter component
 */
const mockAccessRequestService = {
  allAccessRequestsFilter: () => ({
    datasetId: '',
    name: '',
    fromDate: undefined,
    toDate: undefined,
    status: undefined,
  }),
  setAllAccessRequestsFilter: jest.fn(),
};

describe('AccessRequestManagerFilterComponent', () => {
  let component: AccessRequestManagerFilterComponent;
  let fixture: ComponentFixture<AccessRequestManagerFilterComponent>;
  let accessRequestService: AccessRequestService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AccessRequestManagerFilterComponent],
      providers: [
        { provide: AccessRequestService, useValue: mockAccessRequestService },
        provideNativeDateAdapter(),
        provideNoopAnimations(),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AccessRequestManagerFilterComponent);
    component = fixture.componentInstance;
    accessRequestService = TestBed.inject(AccessRequestService);
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should reset the filter upon initialization', async () => {
    expect(accessRequestService.setAllAccessRequestsFilter).toHaveBeenCalledWith({
      datasetId: '',
      name: '',
      fromDate: undefined,
      toDate: undefined,
      status: undefined,
    });
  });

  it('should set the filter after typing a name', async () => {
    const textbox = screen.getByRole('textbox', { name: 'User name' });

    userEvent.type(textbox, 'Doe');
    await fixture.whenStable();

    expect(accessRequestService.setAllAccessRequestsFilter).toHaveBeenCalledWith({
      datasetId: '',
      name: 'Doe',
      fromDate: undefined,
      toDate: undefined,
      status: undefined,
    });
  });

  it('should set the filter after selecting a status', async () => {
    const combobox = screen.getByRole('combobox', { name: 'All status values' });

    userEvent.click(combobox);
    await fixture.whenStable();

    const option = screen.getByRole('option', { name: 'allowed' });
    userEvent.click(option);
    await fixture.whenStable();

    expect(accessRequestService.setAllAccessRequestsFilter).toHaveBeenCalledWith({
      datasetId: '',
      name: '',
      fromDate: undefined,
      toDate: undefined,
      status: AccessRequestStatus.allowed,
    });
  });
});
