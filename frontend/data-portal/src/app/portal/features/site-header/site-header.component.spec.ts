/**
 * Test the site header component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ActivatedRoute } from '@angular/router';

import { screen } from '@testing-library/angular';

import { fakeActivatedRoute } from '@app/../mocks/route';
import { AccountButtonComponent } from '../account-button/account-button.component';
import { SiteHeaderNavButtonsComponent } from '../site-header-nav-buttons/site-header-nav-buttons.component';
import { SiteHeaderComponent } from './site-header.component';

describe('SiteHeaderComponent', () => {
  let component: SiteHeaderComponent;
  let fixture: ComponentFixture<SiteHeaderComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule],
      providers: [
        {
          provide: ActivatedRoute,
          useValue: fakeActivatedRoute,
        },
      ],
    })
      .overrideComponent(SiteHeaderComponent, {
        remove: {
          imports: [AccountButtonComponent, SiteHeaderNavButtonsComponent],
        },
      })
      .compileComponents();
  });

  beforeEach(async () => {
    fixture = TestBed.createComponent(SiteHeaderComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should contain a navigation', () => {
    const navbar = screen.getByRole('navigation');
    expect(navbar).toBeVisible();
  });
});
