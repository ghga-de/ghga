/**
 * Tests for the StatusTextBoxComponent
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { StatusTextBoxComponent } from './status-text-box';

describe('StatusTextBoxComponent', () => {
  let component: StatusTextBoxComponent;
  let fixture: ComponentFixture<StatusTextBoxComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [StatusTextBoxComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(StatusTextBoxComponent);
    fixture.componentRef.setInput('status', 'READY');
    fixture.componentRef.setInput(
      'statusText',
      'Ready. Load a default or paste your content.',
    );
    fixture.detectChanges();
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
