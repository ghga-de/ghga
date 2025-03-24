/**
 * Testing for the site header nav buttons component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ActivatedRoute } from '@angular/router';
import { fakeActivatedRoute } from '@app/../mocks/route';
import { AccountButtonComponent } from '../account-button/account-button.component';
import { AdminMenuComponent } from '../admin-menu/admin-menu.component';
import { SiteHeaderNavButtonsComponent } from './site-header-nav-buttons.component';

describe('SiteHeaderNavButtonsComponent', () => {
  let component: SiteHeaderNavButtonsComponent;
  let fixture: ComponentFixture<SiteHeaderNavButtonsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SiteHeaderNavButtonsComponent],
      providers: [
        {
          provide: ActivatedRoute,
          useValue: fakeActivatedRoute,
        },
      ],
    })
      .overrideComponent(SiteHeaderNavButtonsComponent, {
        remove: {
          imports: [AccountButtonComponent, AdminMenuComponent],
        },
      })
      .compileComponents();

    fixture = TestBed.createComponent(SiteHeaderNavButtonsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
