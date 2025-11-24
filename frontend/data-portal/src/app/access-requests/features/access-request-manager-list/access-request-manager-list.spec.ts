/**
 * Test the Access Request Manager List component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AccessRequestManagerListComponent } from './access-request-manager-list';

import { ActivatedRoute } from '@angular/router';
import { accessRequests } from '@app/../mocks/data';
import { fakeActivatedRoute } from '@app/../mocks/route';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { ConfigService } from '@app/shared/services/config';

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
}

/**
 * Mock the config service as needed by the access request manager list component
 */

const MockConfigService = {
  helpdesk_url: 'https://helpdesk.test',
};

describe('AccessRequestManagerListComponent', () => {
  let component: AccessRequestManagerListComponent;
  let fixture: ComponentFixture<AccessRequestManagerListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AccessRequestManagerListComponent],
      providers: [
        { provide: AccessRequestService, useClass: MockAccessRequestService },
        { provide: ConfigService, useValue: MockConfigService },
        { provide: ActivatedRoute, useValue: fakeActivatedRoute },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AccessRequestManagerListComponent);
    component = fixture.componentInstance;
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
});
