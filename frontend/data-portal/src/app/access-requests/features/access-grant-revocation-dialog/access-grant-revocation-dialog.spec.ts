/**
 * Unit tests for the dialog to revoke access grants
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { render, screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';
import { AccessGrantRevocationDialogComponent } from './access-grant-revocation-dialog';

describe('AccessGrantRevocationDialogComponent', () => {
  let accessRequestService: AccessRequestService;
  let fixture: ComponentFixture<AccessGrantRevocationDialogComponent>;

  const mockDialogRef = {
    close: jest.fn(),
  };

  const testGrantId = 'GHGAD12345678901236';
  const placeholderText = 'Type the Grant ID here';

  beforeEach(async () => {
    const mockAccessRequestService = {
      revokeAccessGrant: jest.fn(),
    };

    const { fixture: renderedFixture } = await render(
      AccessGrantRevocationDialogComponent,
      {
        providers: [
          { provide: AccessRequestService, useValue: mockAccessRequestService },
          { provide: MatDialogRef, useValue: mockDialogRef },
          { provide: MAT_DIALOG_DATA, useValue: { grantID: testGrantId } },
        ],
      },
    );

    fixture = renderedFixture;
    accessRequestService = TestBed.inject(AccessRequestService);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('should create', () => {
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('should have the Revoke button disabled initially', () => {
    const revokeButton = screen.getByRole('button', { name: /revoke/i });
    expect(revokeButton).toBeDisabled();
  });

  it('should enable the Revoke button when the correct grant ID is typed', async () => {
    const revokeButton = screen.getByRole('button', { name: /revoke/i });
    const input = screen.getByPlaceholderText(placeholderText);

    expect(revokeButton).toBeDisabled();

    await userEvent.type(input, testGrantId);

    expect(revokeButton).toBeEnabled();
  });

  it('should keep the Revoke button disabled if the wrong grant ID is typed', async () => {
    const revokeButton = screen.getByRole('button', { name: /revoke/i });
    const input = screen.getByPlaceholderText(placeholderText);

    await userEvent.type(input, 'WRONG-ID');

    expect(revokeButton).toBeDisabled();
  });

  it('should call revokeAccessGrant and close the dialog on successful revocation', async () => {
    (accessRequestService.revokeAccessGrant as jest.Mock).mockResolvedValue(true);

    const revokeButton = screen.getByRole('button', { name: /revoke/i });
    const input = screen.getByPlaceholderText(placeholderText);

    await userEvent.type(input, testGrantId);
    await userEvent.click(revokeButton);

    // Wait for promises to resolve and UI to update
    await fixture.whenStable();

    expect(accessRequestService.revokeAccessGrant).toHaveBeenCalledWith(testGrantId);
    expect(mockDialogRef.close).toHaveBeenCalledWith(true);
  });
});
