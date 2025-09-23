/**
 * Test the dialog component used in the access request manager.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

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
    // uses workaround for jest selector validation issue
    // const heading = screen.getByRole('heading', { level: 1 });
    // expect(heading).toHaveTextContent('Access Request Details');
    const heading = screen.getByText('Access Request Details');
    expect(heading).toBeTruthy();
  });

  it('should show the dataset ID in a link', () => {
    // uses workaround for jest selector validation issue
    // const a = screen.getByRole('link', { name: 'GHGAD12345678901235 (new tab)' });
    // expect(a).toBeVisible();
    const a = screen.getByText('GHGAD12345678901235');
    expect(a).toBeTruthy();
  });

  it('should show the requester with email in two links', () => {
    // uses workaround for jest selector validation issue
    // const a = screen.getByRole('link', { name: 'Dr. John Doe' });
    const a = screen.getByText('Dr. John Doe');
    // expect(a).toBeVisible();
    expect(a).toBeTruthy();
    // const email = screen.getByRole('link', { name: 'doe@home.org' });
    const email = screen.getByText('doe@home.org');
    // expect(email).toBeVisible();
    expect(email).toBeTruthy();
  });

  it('should load the LD ID and show it in a code', () => {
    // uses workaround for jest selector validation issue
    let code = screen.getByText(
      'ls-id-of-joe​@ls-aai.dev',
      // { selector: 'code' }
    );
    // expect(code).toBeVisible();
    expect(code).toBeTruthy();
  });

  it('should show the request details in a paragraph', () => {
    // uses workaround for jest selector validation issue
    const p = screen.getByText(
      'This is a test request for dataset GHGAD12345678901236.',
      //{ selector: 'p' },
    );
    // expect(p).toBeVisible();
    expect(p).toBeTruthy();
  });

  it('should show the first IVA as a radio button and preselected', () => {
    // Workaround for jest selector validation issue
    // const button = screen.getByRole('radio', { name: 'SMS: +441234567890004' });
    const button = screen.getByDisplayValue('783d9682-d5e5-4ce7-9157-9eeb53a1e9ba');
    expect(button).toBeChecked();
  });

  it('should show the third IVA as a radio button and not selected', () => {
    // Workaround for jest selector validation issue
    // const button = screen.getByRole('radio', {
    //  name: 'Postal Address: c/o Weird Al Yankovic, Dr. John Doe, Wilhelmstraße 123, Apartment 25, Floor 2, 72072 Tübingen, Baden-Württemberg, Deutschland',
    //});
    const button = screen.getByText(
      'Postal Address: c/o Weird Al Yankovic, Dr. John Doe, Wilhelmstraße 123, Apartment 25, Floor 2, 72072 Tübingen, Baden-Württemberg, Deutschland',
    );
    expect(button).not.toBeChecked();
  });

  it('should have an enabled allow button', () => {
    // Workaround for jest selector validation issue
    // const button = screen.getByRole('button', { name: 'Allow' });
    const button = screen.getByText('Allow');
    expect(button).toBeEnabled();
  });

  it('should have an enabled deny button', () => {
    // Workaround for jest selector validation issue
    // const button = screen.getByRole('button', { name: 'Deny' });
    const button = screen.getByText('Deny');
    expect(button).toBeEnabled();
  });

  it('should have an enabled back button', () => {
    // Workaround for jest selector validation issue
    // const button = screen.getByRole('button', { name: 'Back' });
    const button = screen.getByText('Back');
    expect(button).toBeEnabled();
  });
});
