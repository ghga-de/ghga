/**
 * Tests for the "with copy button" component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { WithCopyButton } from './with-copy-button';

describe('WithCopyButton', () => {
  let component: WithCopyButton;
  let fixture: ComponentFixture<WithCopyButton>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [WithCopyButton],
    }).compileComponents();

    fixture = TestBed.createComponent(WithCopyButton);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
