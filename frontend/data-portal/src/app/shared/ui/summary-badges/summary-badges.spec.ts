/**
 * Test the summary badges component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SummaryBadgesComponent } from './summary-badges';

describe('SummaryBadgesComponent', () => {
  let componentFourItems: SummaryBadgesComponent;
  let fixtureFourItems: ComponentFixture<SummaryBadgesComponent>;
  let componentThreeItems: SummaryBadgesComponent;
  let fixtureThreeItems: ComponentFixture<SummaryBadgesComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SummaryBadgesComponent],
      providers: [],
    }).compileComponents();

    fixtureFourItems = TestBed.createComponent(SummaryBadgesComponent);
    componentFourItems = fixtureFourItems.componentInstance;
    fixtureFourItems.componentRef.setInput('data', [
      { value: 'test 1', count: 1 },
      { value: 'test 2', count: 1 },
      { value: 'test 3', count: 1 },
      { value: 'test 4', count: 1 },
    ]);
    fixtureThreeItems = TestBed.createComponent(SummaryBadgesComponent);
    componentThreeItems = fixtureThreeItems.componentInstance;
    fixtureThreeItems.componentRef.setInput('data', [
      { value: 'test 1', count: 1 },
      { value: 'test 2', count: 1 },
      { value: 'test 3', count: 1 },
    ]);
    await fixtureFourItems.whenStable();
    await fixtureThreeItems.whenStable();
  });

  it('should create', () => {
    expect(componentFourItems).toBeTruthy();
    expect(componentThreeItems).toBeTruthy();
  });

  it('should show "Show 2 More" when there are four items', () => {
    const compiled = fixtureFourItems.nativeElement as HTMLElement;
    const text = compiled.textContent;
    expect(text).toContain('test 1 1test 2 1Show 2 more…test 3 1test 4 1');
  });

  it('should show all three data points when there are only three', () => {
    const compiled = fixtureThreeItems.nativeElement as HTMLElement;
    const text = compiled.textContent;
    expect(text).toContain('test 1 1test 2 1test 3 1');
  });
});
