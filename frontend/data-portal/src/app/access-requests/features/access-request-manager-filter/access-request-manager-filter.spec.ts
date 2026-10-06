/**
 * Test the Access Request Manager Filter component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { provideNativeDateAdapter } from '@angular/material/core';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { AccessRequestManagerFilter } from './access-request-manager-filter';

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
    ticketId: undefined,
    noteToRequester: undefined,
    internalNote: undefined,
  }),
  setAllAccessRequestsFilter: vitest.fn(),
};

describe('AccessRequestManagerFilter', () => {
  let component: AccessRequestManagerFilter;
  let fixture: ComponentFixture<AccessRequestManagerFilter>;
  let accessRequestService: AccessRequestService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AccessRequestManagerFilter],
      providers: [
        { provide: AccessRequestService, useValue: mockAccessRequestService },
        provideNativeDateAdapter(),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AccessRequestManagerFilter);
    component = fixture.componentInstance;
    accessRequestService = TestBed.inject(AccessRequestService);
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should reset the filter upon initialization', async () => {
    expect(accessRequestService.setAllAccessRequestsFilter).toHaveBeenCalledWith({
      dataset: undefined,
      requester: undefined,
      dac: undefined,
      fromDate: undefined,
      toDate: undefined,
      status: undefined,
      ticketId: undefined,
      noteToRequester: undefined,
      internalNote: undefined,
    });
  });

  it('should set the filter after typing a name', async () => {
    const textbox = screen.getByRole('textbox', { name: 'Name or email of requester' });

    await userEvent.type(textbox, 'Doe');
    await fixture.whenStable();

    expect(accessRequestService.setAllAccessRequestsFilter).toHaveBeenCalledWith({
      dataset: undefined,
      requester: 'Doe',
      dac: undefined,
      fromDate: undefined,
      toDate: undefined,
      status: undefined,
      ticketId: undefined,
      noteToRequester: undefined,
      internalNote: undefined,
    });
  });

  it('should set the filter after typing a ticket id', async () => {
    const textbox = screen.getByRole('textbox', { name: 'Ticket ID' });

    await userEvent.type(textbox, '1559');
    await fixture.whenStable();

    expect(accessRequestService.setAllAccessRequestsFilter).toHaveBeenCalledWith({
      dataset: undefined,
      requester: undefined,
      fromDate: undefined,
      toDate: undefined,
      status: undefined,
      ticketId: '1559',
      noteToRequester: undefined,
      internalNote: undefined,
    });
  });

  it('should set the filter after selecting a status', async () => {
    const combobox = screen.getByRole('combobox', { name: 'All resolutions' });

    await userEvent.click(combobox);
    await fixture.whenStable();

    const option = screen.getByRole('option', { name: 'Allowed' });
    await userEvent.click(option);
    await fixture.whenStable();

    expect(accessRequestService.setAllAccessRequestsFilter).toHaveBeenCalledWith({
      dataset: undefined,
      requester: undefined,
      fromDate: undefined,
      toDate: undefined,
      status: AccessRequestStatus.allowed,
      ticketId: undefined,
      noteToRequester: undefined,
      internalNote: undefined,
    });
  });

  it('should set the filter after typing a note to requester', async () => {
    const textbox = screen.getByRole('textbox', { name: 'Note to requester' });

    await userEvent.type(textbox, 'Please wait for the approval.');
    await fixture.whenStable();

    expect(accessRequestService.setAllAccessRequestsFilter).toHaveBeenCalledWith({
      dataset: undefined,
      requester: undefined,
      fromDate: undefined,
      toDate: undefined,
      status: undefined,
      ticketId: undefined,
      noteToRequester: 'Please wait for the approval.',
      internalNote: undefined,
    });
  });

  it('should set the filter after typing an internal note', async () => {
    const textbox = screen.getByRole('textbox', { name: 'Internal note' });

    await userEvent.type(textbox, 'We need to ask X');
    await fixture.whenStable();

    expect(accessRequestService.setAllAccessRequestsFilter).toHaveBeenCalledWith({
      dataset: undefined,
      requester: undefined,
      fromDate: undefined,
      toDate: undefined,
      status: undefined,
      ticketId: undefined,
      noteToRequester: undefined,
      internalNote: 'We need to ask X',
    });
  });

  /**
   * Get the filter the component sent last
   * @returns the last filter
   */
  function lastFilter() {
    return mockAccessRequestService.setAllAccessRequestsFilter.mock.lastCall![0];
  }

  it('should set the filter after typing a dataset and a DAC', async () => {
    await userEvent.type(
      screen.getByRole('textbox', { name: 'Dataset title or ID' }),
      'GHGAD1',
    );
    await userEvent.type(
      screen.getByRole('textbox', { name: 'Name or email of DAC' }),
      'Main DAC',
    );
    await fixture.whenStable();

    expect(lastFilter()).toMatchObject({ dataset: 'GHGAD1', dac: 'Main DAC' });
  });

  it('should set the filter after typing request details', async () => {
    await userEvent.type(
      screen.getByRole('textbox', { name: 'Request details' }),
      'cancer',
    );
    await fixture.whenStable();

    expect(lastFilter()).toMatchObject({ requestText: 'cancer' });
  });

  it('should set the filter after typing creation dates', async () => {
    await userEvent.type(
      screen.getByRole('textbox', { name: 'Request creation date from' }),
      '1/15/2025',
    );
    await userEvent.type(
      screen.getByRole('textbox', { name: 'Request creation date until' }),
      '2/28/2025',
    );
    await fixture.whenStable();

    expect(lastFilter()).toMatchObject({
      fromDate: new Date(2025, 0, 15),
      toDate: new Date(2025, 1, 28),
    });
  });

  it('should clear the filter with the remove buttons', async () => {
    await userEvent.type(screen.getByRole('textbox', { name: 'Ticket ID' }), '1559');
    await userEvent.type(
      screen.getByRole('textbox', { name: 'Request creation date from' }),
      '1/15/2025',
    );
    await fixture.whenStable();
    expect(lastFilter()).toMatchObject({
      ticketId: '1559',
      fromDate: new Date(2025, 0, 15),
    });

    await userEvent.click(
      screen.getByRole('button', { name: 'Remove filter for ticket ID' }),
    );
    await userEvent.click(
      screen.getByRole('button', { name: 'Remove filter for dates ranging from' }),
    );
    await fixture.whenStable();

    expect(lastFilter().ticketId).toBeFalsy();
    expect(lastFilter().fromDate).toBeFalsy();
    expect(screen.getByRole('textbox', { name: 'Ticket ID' })).toHaveValue('');
    expect(
      screen.getByRole('textbox', { name: 'Request creation date from' }),
    ).toHaveValue('');
  });
});
