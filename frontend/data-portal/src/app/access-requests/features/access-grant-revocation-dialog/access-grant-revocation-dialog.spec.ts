/**
 * Unit tests for the dialog to revoke access grants
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { provideHttpClient } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { accessGrants } from '@app/../mocks/data';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { MockAccessRequestService } from '@app/access-requests/services/access-request.mock-service';
import { ConfigService } from '@app/shared/services/config';
import { screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';
import { AccessGrantRevocationDialogComponent } from './access-grant-revocation-dialog';

const MockConfigService = {
  auth_url: '/test/auth',
};

describe('AccessGrantRevocationDialogComponent', () => {
  let component: AccessGrantRevocationDialogComponent;
  let fixture: ComponentFixture<AccessGrantRevocationDialogComponent>;
  let service: AccessRequestService;

  const dialogRef = {
    close: jest.fn(),
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AccessGrantRevocationDialogComponent],
      providers: [
        {
          provide: MAT_DIALOG_DATA,
          useValue: {
            grant: accessGrants[0],
          },
        },
        { provide: MatDialogRef, useValue: dialogRef },
        { provide: AccessRequestService, useClass: MockAccessRequestService },
        { provide: ConfigService, useValue: MockConfigService },
        provideHttpClient(),
      ],
      teardown: { destroyAfterEach: false },
    }).compileComponents();

    fixture = TestBed.createComponent(AccessGrantRevocationDialogComponent);
    component = fixture.componentInstance;
    service = fixture.debugElement.injector.get(AccessRequestService);
    fixture.detectChanges();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should return false when cancelled', () => {
    jest.spyOn(dialogRef, 'close');
    expect(dialogRef.close).not.toHaveBeenCalled();
    const button = screen.getByRole('button', { name: 'Cancel' });
    expect(button).toBeVisible();
    expect(button).toHaveTextContent('Cancel');
    button.click();
    expect(dialogRef.close).toHaveBeenCalledWith(false);
  });

  it('should call the grant revocation method when confirmed after confirming the user and dataset', async () => {
    const nameInput = screen.getByPlaceholderText('Confirm email of user');
    await userEvent.type(nameInput, 'doe@home.org');
    const datasetInput = screen.getByPlaceholderText('Confirm dataset accession');
    await userEvent.type(datasetInput, 'GHGAD12345678901234');
    const revokeSpy = jest.spyOn(service, 'revokeAccessGrant');
    expect(revokeSpy).not.toHaveBeenCalled();
    const button = screen.getByRole('button', { name: 'Confirm revocation' });
    expect(button).toBeEnabled();
    expect(button).toHaveTextContent('Confirm revocation');
    button.click();
    expect(revokeSpy).toHaveBeenCalledWith(accessGrants[0].id);
  });
});
