/**
 * Test the Access Request Field Editor component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AccessRequestFieldEditComponent } from './access-request-field-edit';

import { accessRequests } from '@app/../mocks/data';
import { ConfigService } from '@app/shared/services/config';

/**
 * Mock the config service as needed by the access request field edit component
 */
class MockConfigService {
  helpdeskTicketUrl = 'http:/helpdesk.test/ticket/';
}

describe('AccessRequestFieldComponent', () => {
  let component: AccessRequestFieldEditComponent;
  let fixture: ComponentFixture<AccessRequestFieldEditComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [{ provide: ConfigService, useClass: MockConfigService }],
      imports: [AccessRequestFieldEditComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(AccessRequestFieldEditComponent);
    fixture.componentRef.setInput('request', accessRequests[0]);
    fixture.componentRef.setInput('name', 'internal_note');
    fixture.componentRef.setInput('label', 'Internal Note');
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
