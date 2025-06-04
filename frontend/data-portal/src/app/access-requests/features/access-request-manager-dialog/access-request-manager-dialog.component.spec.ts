/**
 * Test the dialog component used in the access request manager.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { accessRequests, allIvasOfDoe } from '@app/../mocks/data';
import { IvaService } from '@app/verification-addresses/services/iva.service';
import { AccessRequestManagerDialogComponent } from './access-request-manager-dialog.component';

import {
  AccessRequestService,
  MockAccessRequestService,
} from '@app/access-requests/services/access-request.service';
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
  helpdeskTicketUrl = 'http:/helpdesk.test/ticket/';
}

describe('AccessRequestManagerDialogComponent', () => {
  let component: AccessRequestManagerDialogComponent;
  let fixture: ComponentFixture<AccessRequestManagerDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AccessRequestManagerDialogComponent],
      providers: [
        { provide: IvaService, useClass: MockIvaService },
        { provide: AccessRequestService, useClass: MockAccessRequestService },
        { provide: ConfigService, useClass: MockConfigService },
        {
          provide: MAT_DIALOG_DATA,
          useValue: { ...accessRequests[0], status: 'pending' },
        },
        { provide: MatDialogRef, useValue: {} },
        provideNoopAnimations(),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AccessRequestManagerDialogComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should show the proper heading', () => {
    const heading = screen.getByRole('heading', { level: 2 });
    expect(heading).toHaveTextContent('Access Request Detail');
  });

  it('should show the dataset ID in a table row', () => {
    const row = screen.getByRole('row', { name: 'Dataset ID: GHGAD12345678901234' });
    expect(row).toBeVisible();
  });

  it('should show the requester in a table row', () => {
    const row = screen.getByRole('row', { name: /Requester: Dr. John Doe/i });
    expect(row).toBeVisible();
  });

  it('should show the requester details in a table row', () => {
    const row = screen.getByRole('row', {
      name: 'Request details: This is a test request for dataset GHGAD12345678901234. Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.',
    });
    expect(row).toBeVisible();
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

  it('should have an enabled cancel button', () => {
    const button = screen.getByRole('button', { name: 'Cancel' });
    expect(button).toBeEnabled();
  });
});
