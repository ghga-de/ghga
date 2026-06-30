/**
 * Tests for the Paragraphs component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ParagraphsComponent } from './paragraphs';

describe('ParagraphsComponent', () => {
  let component: ParagraphsComponent;
  let fixture: ComponentFixture<ParagraphsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ParagraphsComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(ParagraphsComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('text', 'Hello\nWorld');
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should show the text in multiple p tags', () => {
    const par = fixture.nativeElement.querySelectorAll('p');
    expect(par.length).toBe(2);
    expect(par[0].textContent).toContain('Hello');
    expect(par[1].textContent).toContain('World');
  });

  it('should show the label when defined', () => {
    fixture.componentRef.setInput('label', 'Test');
    fixture.detectChanges();
    const strong = fixture.nativeElement.querySelector('strong');
    expect(strong).not.toBeNull();
    expect(strong.textContent).toContain('Test: ');
  });
});
