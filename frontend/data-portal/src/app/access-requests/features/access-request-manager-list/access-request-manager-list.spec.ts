/**
 * Test the Access Request Manager List component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AccessRequestManagerList } from './access-request-manager-list';

import { ActivatedRoute } from '@angular/router';
import {
  AccessGrantStatus,
  AccessRequestStatus,
} from '@app/access-requests/models/access-requests';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { accessRequests } from '@app/../mocks/data';
import { fakeActivatedRoute } from '@app/../mocks/route';
import { ConfigService } from '@app/shared/services/config';
import { screen } from '@testing-library/angular';

/**
 * Mock the access request service as needed by the access request manager list component
 */
class MockAccessRequestService {
  allAccessRequests = {
    value: () => accessRequests,
    isLoading: () => false,
    error: () => undefined,
  };
  allAccessRequestsFiltered = () => this.allAccessRequests.value();
  filter = signal<{ status: AccessRequestStatus | undefined }>({
    status: AccessRequestStatus.pending,
  });
  allAccessRequestsFilter = this.filter;
  grantStates = new Map<string, AccessGrantStatus>();
  loadAllAccessGrants = () => undefined;
  grantStateFor = (userId: string, datasetId: string) =>
    this.grantStates.get(`${userId} ${datasetId}`);
}

/**
 * Mock the config service as needed by the access request manager list component
 */

const MockConfigService = {
  helpdeskTicketUrl: 'https://helpdesk.test/ticket/',
};

describe('AccessRequestManagerList', () => {
  let component: AccessRequestManagerList;
  let fixture: ComponentFixture<AccessRequestManagerList>;
  let service: MockAccessRequestService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AccessRequestManagerList],
      providers: [
        { provide: AccessRequestService, useClass: MockAccessRequestService },
        { provide: ConfigService, useValue: MockConfigService },
        { provide: ActivatedRoute, useValue: fakeActivatedRoute },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AccessRequestManagerList);
    component = fixture.componentInstance;
    service = TestBed.inject(
      AccessRequestService,
    ) as unknown as MockAccessRequestService;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should show access request dataset IDs', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const text = compiled.textContent;
    expect(text).toContain('GHGAD12345678901234');
  });

  it('should not show the access column when filtered to pending only', () => {
    expect(component.columns()).not.toContain('grant');
  });

  it('should show the aggregated access state when not filtered to pending only', async () => {
    const ar = accessRequests[0];
    service.grantStates.set(
      `${ar.user_id} ${ar.dataset_id}`,
      AccessGrantStatus.expired,
    );
    service.filter.set({ status: AccessRequestStatus.allowed });
    await fixture.whenStable();
    expect(component.columns()).toContain('grant');
    const text = (fixture.nativeElement as HTMLElement).textContent;
    expect(text).toContain('Access');
    expect(text).toContain('Requested Validity');
    expect(text).toContain('Resolution');
    expect(text).toContain('expired');
  });

  it('should relabel an upcoming grant as "upcoming" in the access column', async () => {
    const ar = accessRequests[0];
    service.grantStates.set(
      `${ar.user_id} ${ar.dataset_id}`,
      AccessGrantStatus.waiting,
    );
    service.filter.set({ status: AccessRequestStatus.allowed });
    await fixture.whenStable();
    const text = (fixture.nativeElement as HTMLElement).textContent;
    expect(text).toContain('upcoming');
    expect(text).not.toContain('waiting');
  });

  it('should link each ticket ID to its own ticket', () => {
    const withTicket = accessRequests.filter((ar) => ar.ticket_id);
    expect(withTicket).toHaveLength(5);
    for (const ar of withTicket) {
      const link = screen.getByRole('link', { name: ar.ticket_id! });
      expect(link).toHaveAttribute(
        'href',
        `https://helpdesk.test/ticket/${ar.ticket_id}`,
      );
    }
  });

  it('should show no ticket link for a request without a ticket', () => {
    const cells = [
      ...(fixture.nativeElement as HTMLElement).querySelectorAll(
        'td.mat-column-ticket',
      ),
    ];
    expect(cells).toHaveLength(accessRequests.length);
    const withoutTicket = cells.filter((cell) => !cell.textContent?.trim());
    expect(withoutTicket).toHaveLength(3);
    for (const cell of withoutTicket) {
      expect(cell.querySelector('a')).toBeNull();
    }
  });
});
