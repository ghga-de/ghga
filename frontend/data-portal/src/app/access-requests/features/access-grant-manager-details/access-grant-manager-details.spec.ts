/**
 * Test the Access Grant Manager Details component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ActivatedRoute } from '@angular/router';
import { accessGrants, allIvasOfDoe } from '@app/../mocks/data';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { MockAccessRequestService } from '@app/access-requests/services/access-request.mock-service';
import { IvaService } from '@app/verification-addresses/services/iva';
import { AccessGrantManagerDetailsComponent } from './access-grant-manager-details';

/**
 * Mock the IVA service as needed by the access grant manager dialog component
 */
class MockIvaService {
  loadAllIvas = () => undefined;
  allIvas = {
    value: () => allIvasOfDoe,
    isLoading: () => false,
    error: () => undefined,
  };
}

describe('AccessGrantManagerDetailsComponent', () => {
  let component: AccessGrantManagerDetailsComponent;
  let fixture: ComponentFixture<AccessGrantManagerDetailsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AccessGrantManagerDetailsComponent],
      providers: [
        { provide: AccessRequestService, useClass: MockAccessRequestService },
        { provide: IvaService, useClass: MockIvaService },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: new Map() } } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AccessGrantManagerDetailsComponent);
    fixture.componentRef.setInput('id', accessGrants[0].id);
    component = fixture.componentInstance;

    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
