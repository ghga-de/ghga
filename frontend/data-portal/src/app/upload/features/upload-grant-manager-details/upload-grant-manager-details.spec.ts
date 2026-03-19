/**
 * Test the Upload Grant Manager Details component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ActivatedRoute } from '@angular/router';
import { uploadBoxes, uploadGrants } from '@app/../mocks/data';
import { fakeActivatedRoute } from '@app/../mocks/route';
import { IvaService } from '@app/ivas/services/iva';
import { UploadBoxService } from '@app/upload/services/upload-box';
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
    await TestBed.configureTestingModule({
      imports: [UploadGrantManagerDetailsComponent],
      providers: [
        { provide: UploadBoxService, useClass: MockUploadBoxService },
        { provide: IvaService, useClass: MockIvaService },
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
});
