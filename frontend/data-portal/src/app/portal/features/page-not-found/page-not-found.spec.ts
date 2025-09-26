/**
 * Test the home page component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PageNotFoundComponent } from './page-not-found';

describe('PageNotFoundComponent', () => {
  let component: PageNotFoundComponent;
  let fixture: ComponentFixture<PageNotFoundComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PageNotFoundComponent],
      providers: [],
    }).compileComponents();

    fixture = TestBed.createComponent(PageNotFoundComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should render the correct content in the <h1> tag', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const h1 = compiled.querySelector('h1');
    expect(h1?.textContent).toBe('Page not found');
  });

  it('should contain the correct description text', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const p = compiled.querySelector('p');
    expect(p?.textContent).toContain(
      "Sorry, we can't seem to find the page you're looking for",
    );
  });
});
