/**
 * Test the Access Request Duration Editor component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AccessRequestDurationEditComponent } from './access-request-duration-edit';

import { accessRequests } from '@app/../mocks/data';
import { AccessRequestStatus } from '@app/access-requests/models/access-requests';
import { ConfigService } from '@app/shared/services/config';
import { localDateToContractIsoUtc } from '@app/shared/utils/date-formats';

/**
 * Mock the config service as needed by the access request duration edit component
 */
class MockConfigService {
  accessGrantMaxDays = 730;
  accessGrantMaxExtend = 5;
  defaultAccessDurationDays = 365;
}

describe('AccessRequestDurationEditComponent', () => {
  let component: AccessRequestDurationEditComponent;
  let fixture: ComponentFixture<AccessRequestDurationEditComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [{ provide: ConfigService, useClass: MockConfigService }],
      imports: [AccessRequestDurationEditComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(AccessRequestDurationEditComponent);
    fixture.componentRef.setInput('request', accessRequests[0]);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should emit ISO UTC date strings with service-contract day boundaries on save', () => {
    const request = {
      ...accessRequests[0],
      status: AccessRequestStatus.pending,
      access_starts: '2025-01-01T00:00:00.000Z',
      access_ends: '2025-01-08T23:59:59.999Z',
    };
    fixture.componentRef.setInput('request', request);
    fixture.detectChanges();

    const fromDate = new Date(2025, 7, 1);
    const untilDate = new Date(2025, 7, 8);

    let emitted: Map<string, string> | undefined;
    component.saved.subscribe((value) => {
      emitted = value as Map<string, string>;
    });

    (component as any).formModel.set({ fromDate, untilDate });
    component.changed();
    component.save();

    expect(emitted).toBeDefined();
    expect(emitted?.get('access_starts')).toBe(localDateToContractIsoUtc(fromDate));
    expect(emitted?.get('access_ends')).toBe(
      localDateToContractIsoUtc(untilDate, true),
    );
  });
});
