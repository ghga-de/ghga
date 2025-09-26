/**
 * Test the Access Request Duration Editor component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AccessRequestDurationEditComponent } from './access-request-duration-edit';

import { accessRequests } from '@app/../mocks/data';
import { ConfigService } from '@app/shared/services/config';

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
});
