/**
 * Tests for the dataset details table component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { WellKnownValueService } from '@app/metadata/services/well-known-value';
import { ConfigService } from '@app/shared/services/config';
import { MockWellKnownValueService } from '../dataset-details/dataset-details.spec';
import { DatasetDetailsTableComponent } from './dataset-details-table';

/**
 * Mock the config service as needed by the dataset details component
 */
class MockConfigService {
  wkvs_url = 'http://mock.dev/wkvs';
}

describe('DatasetDetailsTableComponent', () => {
  let component: DatasetDetailsTableComponent;
  let fixture: ComponentFixture<DatasetDetailsTableComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DatasetDetailsTableComponent],
      providers: [
        { provide: ConfigService, useClass: MockConfigService },
        { provide: WellKnownValueService, useClass: MockWellKnownValueService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DatasetDetailsTableComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
