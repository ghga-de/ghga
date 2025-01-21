/**
 * Test the home page component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { metadataGlobalSummary } from '@app/../mocks/data';
import { MetadataService } from '@app/metadata/services/metadata.service';
import { HomePageComponent } from './home-page.component';

/**
 * Mock the metadata service as needed for the global stats
 */
class MockMetadataService {
  globalSummary = signal(metadataGlobalSummary.resource_stats);
  globalSummaryError = signal(undefined);
  globalSummaryIsLoading = signal(false);
}

describe('HomePageComponent', () => {
  let component: HomePageComponent;
  let fixture: ComponentFixture<HomePageComponent>;

  const fakeActivatedRoute = {
    snapshot: { data: {} },
  } as ActivatedRoute;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HomePageComponent],
      providers: [
        { provide: MetadataService, useClass: MockMetadataService },
        {
          provide: ActivatedRoute,
          useValue: fakeActivatedRoute,
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(HomePageComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should render top heading', () => {
    const fixture = TestBed.createComponent(HomePageComponent);
    const compiled = fixture.nativeElement as HTMLElement;
    const text = compiled.querySelector('h1')?.textContent;
    expect(text).toContain('The German Human Genome-Phenome Archive');
    expect(text).toContain('Data Portal');
  });
});
