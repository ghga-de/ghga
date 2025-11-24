/**
 * Test the Access Request Manager component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AccessRequestService } from '@app/access-requests/services/access-request';
import { AccessRequestManagerComponent } from './access-request-manager';

import { provideNativeDateAdapter } from '@angular/material/core';
import { ActivatedRoute } from '@angular/router';
import { MockAccessRequestService } from '@app/access-requests/services/access-request.mock-service';
import { ConfigService } from '@app/shared/services/config';
import { screen } from '@testing-library/angular';
import { fakeActivatedRoute } from 'src/mocks/route';

/**
 * Mock the config service as needed by the access request manager component
 */

const MockConfigService = {
  helpdesk_url: 'https://helpdesk.test',
};

describe('AccessRequestManagerComponent', () => {
  let component: AccessRequestManagerComponent;
  let fixture: ComponentFixture<AccessRequestManagerComponent>;
  let accessRequestService: AccessRequestService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AccessRequestManagerComponent],
      providers: [
        { provide: AccessRequestService, useClass: MockAccessRequestService },
        { provide: ConfigService, useValue: MockConfigService },
        { provide: ActivatedRoute, useValue: fakeActivatedRoute },
        provideNativeDateAdapter(),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AccessRequestManagerComponent);
    accessRequestService = TestBed.inject(AccessRequestService);
    accessRequestService.loadAllAccessRequests = vitest.fn();
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should show the proper heading', () => {
    const heading = screen.getByRole('heading', { level: 1 });
    expect(heading).toHaveTextContent('Access Request Management');
  });

  it('should load all the access requests upon initialization', () => {
    expect(accessRequestService.loadAllAccessRequests).toHaveBeenCalled();
  });
});
