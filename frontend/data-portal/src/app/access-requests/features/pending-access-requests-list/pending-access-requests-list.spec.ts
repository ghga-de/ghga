/**
 * Tests for the Pending Access Request List Component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ActivatedRoute } from '@angular/router';
import { fakeActivatedRoute } from '@app/../mocks/route';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { MockAccessRequestService } from '@app/access-requests/services/access-request.mock-service';
import { PendingAccessRequestsListComponent } from './pending-access-requests-list';

describe('PendingAccessRequestsListComponent', () => {
  let component: PendingAccessRequestsListComponent;
  let fixture: ComponentFixture<PendingAccessRequestsListComponent>;
  let accessRequestService: AccessRequestService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PendingAccessRequestsListComponent],
      providers: [
        { provide: AccessRequestService, useClass: MockAccessRequestService },
        { provide: ActivatedRoute, useValue: fakeActivatedRoute },
      ],
    }).compileComponents();

    accessRequestService = TestBed.inject(AccessRequestService);
    fixture = TestBed.createComponent(PendingAccessRequestsListComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should fetch the access requests again when refreshed', () => {
    const reload = vitest.spyOn(accessRequestService, 'reloadUserAccessRequests');
    component.refresh();
    expect(reload).toHaveBeenCalledTimes(1);
  });
});
