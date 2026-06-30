/**
 * Test the Access Grant Manager Details component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ActivatedRoute } from '@angular/router';
import { accessGrants, allIvasOfDoe } from '@app/../mocks/data';
import { fakeActivatedRoute } from '@app/../mocks/route';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { MockAccessRequestService } from '@app/access-requests/services/access-request.mock-service';
import { IvaService } from '@app/ivas/services/iva';
import { AccessGrantManagerDetailsComponent } from './access-grant-manager-details';

/**
 * Mock the IVA service as needed by the access grant manager dialog component
 */
class MockIvaService {
  loadUserIvas = () => undefined;
  ivaError = signal<Error | undefined>(undefined);
  userIvas = {
    value: () => allIvasOfDoe,
    isLoading: () => false,
    error: this.ivaError,
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
        { provide: ActivatedRoute, useValue: fakeActivatedRoute },
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

  it('should show an error message when the IVA could not be loaded', () => {
    const ivaService = TestBed.inject(IvaService) as unknown as MockIvaService;
    ivaService.ivaError.set(new Error('Internal server error'));
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('The IVA could not be loaded');
  });
});
