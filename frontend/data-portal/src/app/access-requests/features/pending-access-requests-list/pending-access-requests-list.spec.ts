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

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PendingAccessRequestsListComponent],
      providers: [
        { provide: AccessRequestService, useClass: MockAccessRequestService },
        { provide: ActivatedRoute, useValue: fakeActivatedRoute },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(PendingAccessRequestsListComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
