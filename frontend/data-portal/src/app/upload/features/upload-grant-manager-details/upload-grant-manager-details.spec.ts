/**
 * Test the Upload Grant Manager Details component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialog } from '@angular/material/dialog';

import { ActivatedRoute } from '@angular/router';
import { uploadBoxes, uploadGrants } from '@app/../mocks/data';
import { fakeActivatedRoute } from '@app/../mocks/route';
import { IvaService } from '@app/ivas/services/iva';
import { NavigationTrackingService } from '@app/shared/services/navigation';
import { UploadBoxService } from '@app/upload/services/upload-box';
import { of } from 'rxjs';
import { UploadGrantManagerDetailsComponent } from './upload-grant-manager-details';

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
  userIvas = {
    value: () => [],
    isLoading: () => false,
    error: () => undefined,
  };
}

describe('UploadGrantManagerDetailsComponent', () => {
  let component: UploadGrantManagerDetailsComponent;
  let fixture: ComponentFixture<UploadGrantManagerDetailsComponent>;

  beforeEach(async () => {
    mockNavigationService.back.mockReset();
    mockDialog.open.mockReset();
    mockDialog.open.mockReturnValue({ afterClosed: () => of(false) });

    await TestBed.configureTestingModule({
      imports: [UploadGrantManagerDetailsComponent],
      providers: [
        { provide: UploadBoxService, useClass: MockUploadBoxService },
        { provide: IvaService, useClass: MockIvaService },
        { provide: NavigationTrackingService, useValue: mockNavigationService },
        { provide: MatDialog, useValue: mockDialog },
        { provide: ActivatedRoute, useValue: fakeActivatedRoute },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(UploadGrantManagerDetailsComponent);
    fixture.componentRef.setInput('boxId', testBox.id);
    fixture.componentRef.setInput('grantId', testGrant.id);
    component = fixture.componentInstance;

    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should resolve the grant from the box grants', () => {
    expect(component.grant()).toEqual(testGrant);
  });

  it('should resolve the upload box', () => {
    expect(component.box()).toEqual(testBox);
  });

  it('should include a Grant created entry in the audit log', () => {
    const log = component.sortedLog();
    expect(log.some((entry) => entry.status === 'Grant created')).toBe(true);
  });

  describe('revokeGrant()', () => {
    beforeEach(() => {
      mockNavigationService.back.mockReset();
    });

    it('should navigate back to the upload box details after successful revocation', () => {
      mockDialog.open.mockReturnValue({ afterClosed: () => of(true) });

      component.revokeGrant();

      expect(mockNavigationService.back).toHaveBeenCalledWith([
        '/upload-box-manager',
        testBox.id,
      ]);
    });

    it('should stay on the page when revocation is cancelled', () => {
      mockDialog.open.mockReturnValue({ afterClosed: () => of(false) });

      component.revokeGrant();

      expect(mockNavigationService.back).not.toHaveBeenCalled();
    });
  });
});
