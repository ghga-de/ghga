/**
 * Test the Upload Grant Manager Details component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { MatDialog } from '@angular/material/dialog';
import { uploadBoxes, uploadGrants } from '@app/../mocks/data';
import { IvaService } from '@app/ivas/services/iva';
import { NavigationTracker } from '@app/shared/services/navigation';
import { UploadBoxService } from '@app/upload/services/upload-box';
import { render, RenderResult, screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';
import { of } from 'rxjs';
import { UploadGrantManagerDetails } from './upload-grant-manager-details';

const testBox = uploadBoxes.boxes[0];
const testGrant = uploadGrants[0];

/**
 * Mock UploadBoxService as needed by the upload grant manager details component.
 */
class MockUploadBoxService {
  loadBoxGrants = () => undefined;
  loadUploadBox = () => undefined;
  boxGrants = {
    value: () => uploadGrants,
    isLoading: () => false,
    error: () => undefined,
  };
  uploadBox = {
    value: () => testBox,
    isLoading: () => false,
    error: () => undefined,
  };
  uploadBoxes = () => uploadBoxes.boxes;
}

const mockNavigationService = { back: vitest.fn() };
const mockDialog = {
  open: vitest.fn(() => ({ afterClosed: () => of(false) })),
};

/**
 * Mock IvaService as needed by the upload grant manager details component.
 */
class MockIvaService {
  loadUserIvas = () => undefined;
  ivaError = signal<Error | undefined>(undefined);
  userIvas = {
    value: () => [],
    isLoading: () => false,
    error: this.ivaError,
  };
}

describe('UploadGrantManagerDetails', () => {
  let result: RenderResult<UploadGrantManagerDetails>;
  let component: UploadGrantManagerDetails;

  beforeEach(async () => {
    mockNavigationService.back.mockReset();
    mockDialog.open.mockReset();
    mockDialog.open.mockReturnValue({ afterClosed: () => of(false) });

    result = await render(UploadGrantManagerDetails, {
      providers: [
        { provide: UploadBoxService, useClass: MockUploadBoxService },
        { provide: IvaService, useClass: MockIvaService },
        { provide: NavigationTracker, useValue: mockNavigationService },
        { provide: MatDialog, useValue: mockDialog },
      ],
      inputs: { boxId: testBox.id, grantId: testGrant.id },
      routes: [],
    });
    component = result.fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
    expect(
      screen.getByRole('heading', { level: 1, name: 'Upload Grant Detail' }),
    ).toBeVisible();
  });

  it('should resolve the grant from the box grants', () => {
    expect(component.grant()).toEqual(testGrant);
    expect(
      screen.getByRole('link', {
        name: `${testGrant.user_title} ${testGrant.user_name}`,
      }),
    ).toHaveAttribute('href', `/user-manager/${testGrant.user_id}`);
  });

  it('should resolve the upload box', () => {
    expect(component.box()).toEqual(testBox);
    expect(screen.getByRole('link', { name: testBox.title })).toHaveAttribute(
      'href',
      `/upload-box-manager/${testBox.id}`,
    );
  });

  it('should include a Grant created entry in the audit log', () => {
    const log = component.sortedLog();
    expect(log.some((entry) => entry.status === 'Grant created')).toBe(true);
    expect(screen.getByText('Grant created')).toBeVisible();
  });

  it('should show an error message when the IVA could not be loaded', async () => {
    expect(screen.queryByText(/The IVA could not be loaded/)).toBeNull();

    const ivaService = TestBed.inject(IvaService) as unknown as MockIvaService;
    ivaService.ivaError.set(new Error('Internal server error'));
    await result.fixture.whenStable();

    expect(screen.getByText(/The IVA could not be loaded/)).toBeVisible();
  });

  describe('revokeGrant()', () => {
    beforeEach(() => {
      mockNavigationService.back.mockReset();
    });

    it('should navigate back to the upload box details after successful revocation', async () => {
      mockDialog.open.mockReturnValue({ afterClosed: () => of(true) });

      await userEvent.click(
        screen.getByRole('button', { name: /revoke upload grant/i }),
      );

      expect(mockDialog.open).toHaveBeenCalled();
      expect(mockNavigationService.back).toHaveBeenCalledWith([
        '/upload-box-manager',
        testBox.id,
      ]);
    });

    it('should stay on the page when revocation is cancelled', async () => {
      mockDialog.open.mockReturnValue({ afterClosed: () => of(false) });

      await userEvent.click(
        screen.getByRole('button', { name: /revoke upload grant/i }),
      );

      expect(mockDialog.open).toHaveBeenCalled();
      expect(mockNavigationService.back).not.toHaveBeenCalled();
    });
  });
});
