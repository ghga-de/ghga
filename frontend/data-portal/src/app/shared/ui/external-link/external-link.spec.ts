/**
 * Test the external link directive
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ChangeDetectionStrategy, Component } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ExternalLinkDirective } from './external-link';

/**
 * Test component to apply the directive
 */
@Component({
  template: `
    <a id="plain" appExtLink>Test Link</a>
    <a id="with-elements" appExtLink><span class="icon"></span>GHGA Website</a>
    <a id="with-aria" appExtLink aria-label="Custom Label">Docs</a>
  `,
  imports: [ExternalLinkDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
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
    const anchor = fixture.nativeElement.querySelector('#plain');
    expect(anchor.getAttribute('target')).toBe('_blank');
  });

  it('should set aria-label with (new tab)', () => {
    const anchor = fixture.nativeElement.querySelector('#plain');
    expect(anchor.getAttribute('aria-label')).toBe('Test Link (new tab)');
  });

  it('should add rel="noreferrer noopener"', () => {
    const anchor = fixture.nativeElement.querySelector('#plain');
    expect(anchor.getAttribute('rel')).toBe('noreferrer noopener');
  });

  it('should preserve existing child elements', () => {
    const anchor = fixture.nativeElement.querySelector('#with-elements');
    expect(anchor.querySelector('.icon')).not.toBeNull();
    expect(anchor.textContent).toContain('GHGA Website');
  });

  it('should preserve existing aria-label', () => {
    const anchor = fixture.nativeElement.querySelector('#with-aria');
    expect(anchor.getAttribute('aria-label')).toBe('Custom Label');
  });
});
