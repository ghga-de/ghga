/**
 * Test the shared refresh button.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { within } from '@testing-library/angular';
import { RefreshButtonComponent } from './refresh-button';

describe('RefreshButtonComponent', () => {
  let fixture: ComponentFixture<RefreshButtonComponent>;

  // Spec files share one document, since the test builder does not isolate them,
  // so a global query can also see buttons left behind by another spec. Look for
  // the button inside the component under test instead.
  const button = () => within(fixture.nativeElement).getByRole('button');

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RefreshButtonComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(RefreshButtonComponent);
    fixture.componentRef.setInput('what', 'the file list');
    await fixture.whenStable();
  });

  it('should name what it refreshes', () => {
    expect(button()).toBeVisible();
    expect(button()).toHaveAccessibleName('Refresh the file list');
  });

  it('should emit when clicked', async () => {
    const refresh = vitest.fn();
    fixture.componentInstance.refresh.subscribe(refresh);
    button().click();
    expect(refresh).toHaveBeenCalledTimes(1);
  });

  it('should be disabled while loading', async () => {
    fixture.componentRef.setInput('loading', true);
    await fixture.whenStable();
    expect(button()).toBeDisabled();
  });

  it('should be disabled when explicitly disabled', async () => {
    fixture.componentRef.setInput('disabled', true);
    await fixture.whenStable();
    expect(button()).toBeDisabled();
  });

  it('should report the umami event when given', async () => {
    fixture.componentRef.setInput('umamiEvent', 'Some Refresh Clicked');
    await fixture.whenStable();
    expect(button()).toHaveAttribute('data-umami-event', 'Some Refresh Clicked');
  });
});
