/**
 * Test the site footer component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';
import { fakeActivatedRoute } from '@app/../mocks/route';
import { SiteFooterComponent } from './site-footer';

describe('SiteFooterComponent', () => {
  let component: SiteFooterComponent;
  let fixture: ComponentFixture<SiteFooterComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SiteFooterComponent],
      providers: [
        {
          provide: ActivatedRoute,
          useValue: fakeActivatedRoute,
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(SiteFooterComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
