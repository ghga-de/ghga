/**
 * Test the external link directive
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ExternalLinkDirective } from './external-link.directive';

/**
 * Test component to apply the directive
 */
@Component({
  template: `<a appExtLink>Test Link</a>`,
  imports: [ExternalLinkDirective],
})
class TestComponent {}

describe('ExternalLinkDirective', () => {
  let fixture: ComponentFixture<TestComponent>;

  beforeEach(async () => {
    fixture = TestBed.createComponent(TestComponent);
    await fixture.whenStable();
    fixture.detectChanges();
  });

  it('should add target="_blank"', () => {
    const anchor = fixture.nativeElement.querySelector('a');
    expect(anchor.getAttribute('target')).toBe('_blank');
  });

  it('should set aria-label with (new tab)', () => {
    const anchor = fixture.nativeElement.querySelector('a');
    expect(anchor.getAttribute('aria-label')).toBe('Test Link (new tab)');
  });

  it('should add rel="noreferrer noopener"', () => {
    const anchor = fixture.nativeElement.querySelector('a');
    expect(anchor.getAttribute('rel')).toBe('noreferrer noopener');
  });
});
