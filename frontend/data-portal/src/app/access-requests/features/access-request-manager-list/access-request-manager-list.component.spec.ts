/**
 * Test the Access Request Manager List component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AccessRequestManagerListComponent } from './access-request-manager-list.component';

import { accessRequests } from '@app/../mocks/data';
import { AccessRequestService } from '@app/access-requests/services/access-request.service';

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

describe('AccessRequestManagerListComponent', () => {
  let component: AccessRequestManagerListComponent;
  let fixture: ComponentFixture<AccessRequestManagerListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AccessRequestManagerListComponent],
      providers: [
        { provide: AccessRequestService, useClass: MockAccessRequestService },
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
