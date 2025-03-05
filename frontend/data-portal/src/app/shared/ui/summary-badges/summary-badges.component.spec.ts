/**
 * Test the summary badges component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SummaryBadgesComponent } from './summary-badges.component';

describe('SummaryBadgesComponent', () => {
  let component: SummaryBadgesComponent;
  let fixture: ComponentFixture<SummaryBadgesComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SummaryBadgesComponent],
      providers: [],
    }).compileComponents();

    fixture = TestBed.createComponent(SummaryBadgesComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('data', [
      { value: 'test 1', count: 1 },
      { value: 'test 2', count: 1 },
      { value: 'test 3', count: 1 },
      { value: 'test 4', count: 1 },
    ]);
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should show "Show 1 More" type', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const text = compiled.textContent;
    expect(text).toContain('Show 1 more');
  });
});
