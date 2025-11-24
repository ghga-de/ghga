/**
 * Test the Access Grant Manager component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ActivatedRoute } from '@angular/router';
import { fakeActivatedRoute } from '@app/../mocks/route';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { AccessGrantManagerComponent } from './access-grant-manager';

import { MockAccessRequestService } from '@app/access-requests/services/access-request.mock-service';

describe('AccessGrantManagerComponent', () => {
  let component: AccessGrantManagerComponent;
  let fixture: ComponentFixture<AccessGrantManagerComponent>;
  let accessRequestService: AccessRequestService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AccessGrantManagerComponent],
      providers: [
        { provide: AccessRequestService, useClass: MockAccessRequestService },
        { provide: ActivatedRoute, useValue: fakeActivatedRoute },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AccessGrantManagerComponent);
    accessRequestService = TestBed.inject(AccessRequestService);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
