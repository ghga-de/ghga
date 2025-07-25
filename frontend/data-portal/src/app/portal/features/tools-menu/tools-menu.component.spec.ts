/**
 * Test the tools menu component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ActivatedRoute } from '@angular/router';
import { ToolsMenuComponent } from './tools-menu.component';

const fakeActivatedRoute = {
  snapshot: { data: {}, url: [{ path: 'schemapack-playground' }] },
} as ActivatedRoute;

describe('ToolsMenuComponent', () => {
  let component: ToolsMenuComponent;
  let fixture: ComponentFixture<ToolsMenuComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ToolsMenuComponent],
      providers: [
        {
          provide: ActivatedRoute,
          useValue: fakeActivatedRoute,
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ToolsMenuComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
