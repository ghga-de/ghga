/**
 * Test the dialog component used in the access request manager.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { allIvasOfDoe } from '@app/../mocks/data';
import { IvaService } from '@app/verification-addresses/services/iva.service';
import { AccessRequestManagerDetailComponent } from './access-request-manager-detail.component';

import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { ActivatedRoute } from '@angular/router';
import { MockAccessRequestService } from '@app/access-requests/services/access-request.mock-service';
import { AccessRequestService } from '@app/access-requests/services/access-request.service';
import { ConfigService } from '@app/shared/services/config.service';
import { screen } from '@testing-library/angular';

/**
 * Mock the IVA service as needed by the access request manager dialog component
 */
class MockIvaService {
  loadUserIvas = () => undefined;
  userIvas = {
    value: () => allIvasOfDoe,
    isLoading: () => false,
    error: () => undefined,
  };
}

/**
 * Mock the config service as needed by the access request manager dialog component
 */
class MockConfigService {
  authUrl = 'http://mock.dev/auth';
  helpdeskTicketUrl = 'http:/helpdesk.test/ticket/';
}

describe('AccessRequestManagerDetailComponent', () => {
  let component: AccessRequestManagerDetailComponent;
  let fixture: ComponentFixture<AccessRequestManagerDetailComponent>;
  let httpMock: HttpTestingController;
  let testBed: TestBed;

  beforeEach(async () => {
    testBed = TestBed.configureTestingModule({
      imports: [AccessRequestManagerDetailComponent],
      providers: [
        { provide: IvaService, useClass: MockIvaService },
        { provide: AccessRequestService, useClass: MockAccessRequestService },
        { provide: ConfigService, useClass: MockConfigService },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: new Map() } } },
        provideHttpClient(),
        provideHttpClientTesting(),
        provideNoopAnimations(),
      ],
    });

    await testBed.compileComponents();
    fixture = testBed.createComponent(AccessRequestManagerDetailComponent);
    component = fixture.componentInstance;
    httpMock = testBed.inject(HttpTestingController);

    fixture.componentRef.setInput('id', '9409db13-e23e-433e-9afa-544d8f25b720');

    testBed.tick();
    const req = httpMock.expectOne('http://mock.dev/auth/users/doe@test.dev');
    expect(req.request.method).toBe('GET');
    req.flush({ ext_id: 'ls-id-of-joe@ls-aai.dev' });

    await fixture.whenStable();
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should show the proper heading', () => {
    const heading = screen.getByRole('heading', { level: 1 });
    expect(heading).toHaveTextContent('Access Request Details');
  });

  it('should show the dataset ID in a link', () => {
    const a = screen.getByRole('link', { name: 'GHGAD12345678901235' });
    expect(a).toBeVisible();
  });

  it('should show the requester with email in two links', () => {
    const a = screen.getByRole('link', { name: 'Dr. John Doe' });
    expect(a).toBeVisible();
    const email = screen.getByRole('link', { name: 'doe@home.org' });
    expect(email).toBeVisible();
  });

  it('should load the LD ID and show it in a code', () => {
    let code = screen.getByText('ls-id-of-joe​@ls-aai.dev', { selector: 'code' });
    expect(code).toBeVisible();
  });

  it('should show the request details in a paragraph', () => {
    const p = screen.getByText(
      'This is a test request for dataset GHGAD12345678901236.',
      { selector: 'p' },
    );
    expect(p).toBeVisible();
  });

  it('should show the first IVA as a radio button and preselected', () => {
    const button = screen.getByRole('radio', { name: 'SMS: +441234567890004' });
    expect(button).toBeChecked();
  });

  it('should show the third IVA as a radio button and not selected', () => {
    const button = screen.getByRole('radio', {
      name: 'Postal Address: c/o Weird Al Yankovic, Dr. John Doe, Wilhelmstraße 123, Apartment 25, Floor 2, 72072 Tübingen, Baden-Württemberg, Deutschland',
    });
    expect(button).not.toBeChecked();
  });

  it('should have an enabled allow button', () => {
    const button = screen.getByRole('button', { name: 'Allow' });
    expect(button).toBeEnabled();
  });

  it('should have an enabled deny button', () => {
    const button = screen.getByRole('button', { name: 'Deny' });
    expect(button).toBeEnabled();
  });

  it('should have an enabled back button', () => {
    const button = screen.getByRole('button', { name: 'Back' });
    expect(button).toBeEnabled();
  });
});
