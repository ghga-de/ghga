/**
 * Test the home page component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ActivatedRoute } from '@angular/router';
import { GlobalSummaryComponent } from '@app/metadata/features/global-summary/global-summary.component';
import { HomePageComponent } from './home-page.component';

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
        {
          provide: ActivatedRoute,
          useValue: fakeActivatedRoute,
        },
      ],
    })
      .overrideComponent(HomePageComponent, {
        remove: { imports: [GlobalSummaryComponent] },
      })
      .compileComponents();

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
