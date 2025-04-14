/**
 * Test the dataset summary component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ActivatedRoute } from '@angular/router';
import { datasetSummary, searchResults } from '@app/../mocks/data';
import { fakeActivatedRoute } from '@app/../mocks/route';
import {
  AccessRequestService,
  MockAccessRequestService,
} from '@app/access-requests/services/access-request.service';
import { AuthService } from '@app/auth/services/auth.service';
import { DatasetSummaryComponent } from './dataset-summary.component';

/**
 * Mock the auth service as needed for the Dataset Summary Component
 */
class MockAuthService {
  fullName = () => 'Dr. John Doe';
  email = () => 'doe@home.org';
  roles = () => ['data_steward'];
  roleNames = () => ['Data Steward'];
}

describe('DatasetSummaryComponent', () => {
  let component: DatasetSummaryComponent;
  let fixture: ComponentFixture<DatasetSummaryComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DatasetSummaryComponent],
      providers: [
        {
          provide: ActivatedRoute,
          useValue: fakeActivatedRoute,
        },
        { provide: AccessRequestService, useClass: MockAccessRequestService },
        { provide: AuthService, useClass: MockAuthService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DatasetSummaryComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('hit', searchResults.hits.at(0));
    fixture.componentRef.setInput('summary', datasetSummary);
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should show accession and title', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const text = compiled.textContent;
    expect(text).toContain('GHGAD12345678901234');
    expect(text).toContain('Test dataset for details');
  });
});
