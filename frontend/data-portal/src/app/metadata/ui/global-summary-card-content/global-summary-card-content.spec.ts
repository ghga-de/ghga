/**
 * Test the global summary card content component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ActivatedRoute, RouterModule } from '@angular/router';
import { fakeActivatedRoute } from '@app/../mocks/route';
import { screen } from '@testing-library/angular';
import { GlobalSummaryCardContentComponent } from './global-summary-card-content';

describe('GlobalSummaryCardContentComponent', () => {
  let component: GlobalSummaryCardContentComponent;
  let fixture: ComponentFixture<GlobalSummaryCardContentComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [GlobalSummaryCardContentComponent],
      providers: [
        RouterModule,
        { provide: ActivatedRoute, useValue: fakeActivatedRoute },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(GlobalSummaryCardContentComponent);
    fixture.componentRef.setInput('isLoading', false);
    fixture.componentRef.setInput('data', [{ count: 20, value: 'Test item' }]);
    fixture.componentRef.setInput('caption', 'Test');
    fixture.componentRef.setInput('propertyName', 'Test Property');
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should show the correct data', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    fixture.detectChanges();
    const item = compiled.getElementsByTagName('td');
    expect(item.length).toBe(2);
    expect(item[0].textContent).toBe('20');
    expect(item[1].textContent).toBe('Test item');
  });

  it('should show the correct caption', () => {
    const caption = screen.getByRole('caption', { hidden: true });
    expect(caption.textContent).toBe('Test');
  });

  it('should show the correct table headers', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    fixture.detectChanges();
    const item = compiled.getElementsByTagName('th');
    expect(item.length).toBe(2);
    expect(item[0].textContent).toBe('Count');
    expect(item[1].textContent).toBe('Test Property');
  });
});
