/**
 * Test the Access Request Field Editor component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AccessRequestFieldEditComponent } from './access-request-field-edit';

import { accessRequests } from '@app/../mocks/data';
import { ConfigService } from '@app/shared/services/config';
import { screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';

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

  describe('for the ticket ID', () => {
    beforeEach(async () => {
      fixture.componentRef.setInput('request', accessRequests[4]);
      fixture.componentRef.setInput('name', 'ticket_id');
      fixture.componentRef.setInput('label', 'Ticket ID');
      await fixture.whenStable();
      await userEvent.click(fixture.nativeElement.querySelector('.edit-button'));
      await fixture.whenStable();
    });

    it('should strip the base URL from a pasted ticket link', async () => {
      const input = screen.getByRole('textbox');
      await userEvent.clear(input);
      await userEvent.click(input);
      await userEvent.paste('http:/helpdesk.test/ticket/GSI-1234');
      await fixture.whenStable();

      expect(input).toHaveValue('GSI-1234');
    });

    it('should keep a ticket ID without a link', async () => {
      const input = screen.getByRole('textbox');
      await userEvent.clear(input);
      await userEvent.type(input, 'GSI-1234');
      await fixture.whenStable();

      expect(input).toHaveValue('GSI-1234');
    });
  });
});
