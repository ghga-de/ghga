/**
 * Test the dialog component used in the access request manager.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { accessRequests, allIvasOfDoe } from '@app/../mocks/data';
import { IvaService } from '@app/ivas/services/iva';
import { AccessRequestManagerDetail } from './access-request-manager-detail';

import { HttpErrorResponse, provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { provideNativeDateAdapter } from '@angular/material/core';
import { MatDialog } from '@angular/material/dialog';
import { ActivatedRoute } from '@angular/router';
import { fakeActivatedRoute } from '@app/../mocks/route';
import {
  AccessRequest,
  AccessRequestStatus,
} from '@app/access-requests/models/access-requests';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { MockAccessRequestService } from '@app/access-requests/services/access-request.mock-service';
import { ConfigService } from '@app/shared/services/config';
import { ConfirmationService } from '@app/shared/services/confirmation';
import { Notifier } from '@app/shared/services/notification';
import { toMarkup } from '@app/shared/utils/html';
import { screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';
import { of, throwError } from 'rxjs';

/**
 * Mock the IVA service as needed by the access request manager dialog component
 */
class MockIvaService {
  loadUserIvas = () => undefined;
  ivas = allIvasOfDoe;
  userIvas = {
    value: () => this.ivas,
    isLoading: signal(false),
    error: () => undefined,
  };
}

/**
 * Mock the config service as needed by the access request manager dialog component
 */
class MockConfigService {
  authUrl = 'http://mock.dev/auth';
  helpdeskTicketUrl = 'http:/helpdesk.test/ticket/';
  accessGrantMinDays = 7;
}

const DAY_MS = 24 * 60 * 60 * 1000;

let fixture: ComponentFixture<AccessRequestManagerDetail>;
let httpMock: HttpTestingController;

/**
 * Render the component for the mock request, changed as given.
 * @param changes - the fields of the mock request to change
 */
async function render(changes: Partial<AccessRequest> = {}): Promise<void> {
  TestBed.configureTestingModule({
    imports: [AccessRequestManagerDetail],
    providers: [
      { provide: IvaService, useClass: MockIvaService },
      { provide: AccessRequestService, useClass: MockAccessRequestService },
      { provide: ConfigService, useClass: MockConfigService },
      { provide: ActivatedRoute, useValue: fakeActivatedRoute },
      provideHttpClient(),
      provideHttpClientTesting(),
      provideNativeDateAdapter(),
    ],
  });

  await TestBed.compileComponents();
  // the mock data types the status as a plain string
  TestBed.inject(AccessRequestService).accessRequest.value.set({
    ...accessRequests[4],
    ...changes,
  } as AccessRequest);
  fixture = TestBed.createComponent(AccessRequestManagerDetail);
  httpMock = TestBed.inject(HttpTestingController);

  fixture.componentRef.setInput('id', '9409db13-e23e-433e-9afa-544d8f25b720');

  TestBed.tick();
  const req = httpMock.expectOne('http://mock.dev/auth/users/doe@test.dev');
  expect(req.request.method).toBe('GET');
  req.flush({ ext_id: 'ls-id-of-joe@ls-aai.dev', email: 'joe@login.org' });

  await fixture.whenStable();
}

describe('AccessRequestManagerDetail', () => {
  beforeEach(() => render());

  afterEach(() => {
    httpMock.verify();
  });

  it('should show the proper heading', () => {
    const heading = screen.getByRole('heading', { level: 1 });
    expect(heading).toHaveTextContent('Access Request Details');
  });

  it('should show the dataset ID in a link', () => {
    const a = screen.getByRole('link', { name: 'GHGAD12345678901235 (new tab)' });
    expect(a).toBeVisible();
  });

  it('should show the requester and the contact email in two links', () => {
    const a = screen.getByRole('link', { name: 'Dr. John Doe' });
    expect(a).toBeVisible();
    const email = screen.getByRole('link', { name: 'doe@home.org' });
    expect(email).toBeVisible();
    expect(email.closest('p')).toHaveTextContent(/^\s*Contact email:/);
  });

  it('should load the LS Login email and show it in a link', () => {
    const email = screen.getByRole('link', { name: 'joe@login.org' });
    expect(email).toBeVisible();
    expect(email.closest('p')).toHaveTextContent(/^\s*LS Login email:/);
  });

  it('should load the LD ID and show it in a code', () => {
    const code = screen.getByText('ls-id-of-joe​@ls-aai.dev', { selector: 'code' });
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

  it('should show an Access Grants card', () => {
    const heading = screen.getByRole('heading', { name: 'Access Grants' });
    expect(heading).toBeVisible();
  });

  it('should show the current aggregated access state', () => {
    const state = screen.getByText(/Current access state is/);
    expect(state).toHaveTextContent('Current access state is active');
  });

  it('should announce the number of corresponding access grants', () => {
    // The viewed request (doe@test.dev / GHGAD12345678901235) is modelled as a
    // renewal in the mock data, so it has two corresponding grants.
    const sentence = screen.getByText('There are 2 corresponding access grants:');
    expect(sentence).toBeVisible();
  });

  it('should list each grant validity period as a link to its details', () => {
    const links = screen.getAllByRole('link', {
      name: /\d{4}-\d{2}-\d{2} until \d{4}-\d{2}-\d{2}/,
    });
    expect(links).toHaveLength(2);
    const hrefs = links.map((link) => link.getAttribute('href'));
    expect(hrefs).toContain('/access-grant-manager/grant-ghga-8c4b9d5a1f0b');
  });

  it('should escape the address in the approval dialog', () => {
    const confirm = vitest
      .spyOn(TestBed.inject(ConfirmationService), 'confirm')
      .mockImplementation(() => undefined);
    const ivaService = TestBed.inject(IvaService) as unknown as MockIvaService;
    ivaService.ivas = allIvasOfDoe.map((iva) => ({ ...iva, value: '<b>x</b>' }));

    fixture.componentInstance.safeAllow();

    expect(confirm).toHaveBeenCalledTimes(1);
    expect(toMarkup(confirm.mock.calls[0][0].message)).toContain(
      ': &lt;b&gt;x&lt;/b&gt;.',
    );
  });

  it('should save the IVA that the data steward selects', async () => {
    const updateRequest = vitest.fn(() => of(undefined));
    Object.assign(TestBed.inject(AccessRequestService), { updateRequest });
    const button = screen.getByRole('radio', {
      name: 'Postal Address: c/o Weird Al Yankovic, Dr. John Doe, Wilhelmstraße 123, Apartment 25, Floor 2, 72072 Tübingen, Baden-Württemberg, Deutschland',
    });

    await userEvent.click(button);
    await fixture.whenStable();

    expect(button).toBeChecked();
    expect(updateRequest).toHaveBeenCalledExactlyOnceWith(
      '9409db13-e23e-433e-9afa-544d8f25b720',
      { iva_id: allIvasOfDoe[2].id },
    );
  });

  /**
   * Select the postal address IVA, which is not the best one, and reload the IVAs.
   * @returns the radio button of the postal address
   */
  async function selectPostalIvaAndReload(): Promise<HTMLElement> {
    const postal = screen.getByRole('radio', {
      name: 'Postal Address: c/o Weird Al Yankovic, Dr. John Doe, Wilhelmstraße 123, Apartment 25, Floor 2, 72072 Tübingen, Baden-Württemberg, Deutschland',
    });
    await userEvent.click(postal);
    await fixture.whenStable();
    expect(postal).toBeChecked();

    const ivas = (TestBed.inject(IvaService) as unknown as MockIvaService).userIvas;
    ivas.isLoading.set(true);
    await fixture.whenStable();
    ivas.isLoading.set(false);
    await fixture.whenStable();
    return postal;
  }

  it('should preselect the best IVA again when the IVAs reload', async () => {
    const error = new HttpErrorResponse({ status: 500 });
    Object.assign(TestBed.inject(AccessRequestService), {
      updateRequest: () => throwError(() => error),
    });
    vitest.spyOn(console, 'debug').mockImplementation(() => undefined);

    await selectPostalIvaAndReload();

    expect(screen.getByRole('radio', { name: 'SMS: +441234567890004' })).toBeChecked();
  });

  it('should keep a saved IVA when the IVAs reload', async () => {
    const postal = await selectPostalIvaAndReload();

    expect(postal).toBeChecked();
  });

  it('should show the reason when the backend refuses a change', () => {
    const showError = vitest.spyOn(TestBed.inject(Notifier), 'showError');
    const detail = 'Access end date must be later than access start date';
    const error = new HttpErrorResponse({ status: 422, error: { detail } });
    Object.assign(TestBed.inject(AccessRequestService), {
      updateRequest: () => throwError(() => error),
    });
    vitest.spyOn(console, 'debug').mockImplementation(() => undefined);

    fixture.componentInstance.saveIva();

    expect(showError).toHaveBeenCalledExactlyOnceWith(
      `Access request could not be modified: ${detail}`,
    );
  });

  it('should show a generic message when the backend fails', () => {
    const showError = vitest.spyOn(TestBed.inject(Notifier), 'showError');
    const error = new HttpErrorResponse({ status: 500, error: { detail: 'Boom' } });
    Object.assign(TestBed.inject(AccessRequestService), {
      updateRequest: () => throwError(() => error),
    });
    vitest.spyOn(console, 'debug').mockImplementation(() => undefined);

    fixture.componentInstance.saveIva();

    expect(showError).toHaveBeenCalledExactlyOnceWith(
      'Access request could not be modified. Please try again later',
    );
  });
});

describe('AccessRequestManagerDetail access period warning', () => {
  afterEach(() => {
    httpMock.verify();
  });

  /**
   * Get an ISO date the given number of days from now.
   * @param days - the number of days, negative for the past
   * @returns the date in ISO format
   */
  const daysFromNow = (days: number) =>
    new Date(Date.now() + days * DAY_MS).toISOString();

  it('should not warn when enough of the access period remains', async () => {
    await render();

    expect(screen.queryByText(/access period/)).toBeNull();
  });

  it('should warn when the access period has ended', async () => {
    await render({ access_starts: daysFromNow(-30), access_ends: daysFromNow(-23) });

    expect(
      screen.getByText(/The requested access period ended on \d{4}-\d{2}-\d{2}\./),
    ).toBeVisible();
    expect(screen.getByText(/Set a new end date before allowing/)).toBeVisible();
  });

  it('should explain an ended access period when allowing', async () => {
    await render({ access_starts: daysFromNow(-30), access_ends: daysFromNow(-23) });
    const confirm = vitest
      .spyOn(TestBed.inject(ConfirmationService), 'confirm')
      .mockImplementation(({ callback }) => callback?.(true));
    const updateRequest = vitest.spyOn(
      TestBed.inject(AccessRequestService),
      'updateRequest',
    );

    await userEvent.click(screen.getByRole('button', { name: 'Allow' }));
    await fixture.whenStable();

    expect(confirm).toHaveBeenCalledOnce();
    const { title, confirmText } = confirm.mock.calls[0][0];
    expect(title).toBe('The access period has ended');
    expect(confirmText).toBe('Edit access duration');
    expect(updateRequest).not.toHaveBeenCalled();
    expect(screen.getByLabelText('End date')).toBeVisible();
  });

  it('should warn when less than the minimum access period remains', async () => {
    await render({ access_ends: daysFromNow(3) });

    expect(
      screen.getByText(/The access period ends on .*, which leaves less than 7 days/),
    ).toBeVisible();
  });

  it('should warn when a later access period is shorter than the minimum', async () => {
    await render({ access_starts: daysFromNow(20), access_ends: daysFromNow(22) });

    expect(screen.getByText(/which leaves less than 7 days of access/)).toBeVisible();
  });

  it('should not warn about a request that is no longer pending', async () => {
    await render({
      status: AccessRequestStatus.denied,
      access_starts: daysFromNow(-30),
      access_ends: daysFromNow(-23),
    });

    expect(screen.queryByText(/access period/)).toBeNull();
  });

  it('should warn once the access period ends while the page is open', async () => {
    vitest.useFakeTimers({ toFake: ['setInterval', 'clearInterval', 'Date'] });
    try {
      await render({ access_ends: new Date(Date.now() + 30_000).toISOString() });
      expect(screen.getByText(/which leaves less than 7 days/)).toBeVisible();

      vitest.advanceTimersByTime(60_000);
      await fixture.whenStable();

      expect(screen.getByText(/The requested access period ended on/)).toBeVisible();
    } finally {
      vitest.useRealTimers();
    }
  });

  it('should drop the warning once a new end date is saved', async () => {
    await render({ access_ends: daysFromNow(-1) });

    fixture.componentInstance.saved(new Map([['access_ends', daysFromNow(30)]]));
    await fixture.whenStable();

    expect(screen.queryByText(/access period/)).toBeNull();
  });

  it('should offer to send a verification code for a pending request', async () => {
    await render({ status: AccessRequestStatus.pending });
    expect(
      screen.getByRole('button', { name: /Send verification code to DAC/ }),
    ).toBeVisible();
  });

  it('should not offer to send a verification code for a processed request', async () => {
    await render({ status: AccessRequestStatus.denied });
    expect(
      screen.queryByRole('button', { name: /Send verification code to DAC/ }),
    ).toBeNull();
  });

  it('should show the new internal note after sending a verification code', async () => {
    await render({ status: AccessRequestStatus.pending, internal_note: null });
    const note = '2026-11-10: Verification code AB23CD sent to +49…4242 by Rod.';
    const open = vitest
      .spyOn(TestBed.inject(MatDialog), 'open')
      .mockReturnValue({ afterClosed: () => of(note) } as never);

    await userEvent.click(
      screen.getByRole('button', { name: /Send verification code to DAC/ }),
    );
    await fixture.whenStable();

    expect(open).toHaveBeenCalledOnce();
    expect(fixture.componentInstance.request()?.internal_note).toBe(note);
  });
});
