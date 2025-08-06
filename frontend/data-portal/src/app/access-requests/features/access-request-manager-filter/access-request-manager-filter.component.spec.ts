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
    ticketId: undefined,
    noteToRequester: undefined,
    internalNote: undefined,
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
    const combobox = screen.getByRole('combobox', { name: 'All request statuses' });

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
});
