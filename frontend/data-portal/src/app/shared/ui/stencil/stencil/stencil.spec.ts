/**
 * Test the stencil component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { StencilComponent } from './stencil';

describe('StencilComponent', () => {
  let component: StencilComponent;
  let fixture: ComponentFixture<StencilComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [StencilComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(StencilComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
