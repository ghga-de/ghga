/**
 * This module contains the tests for the GrantedAccessGrantsListComponent.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { provideHttpClient } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { MockAccessRequestService } from '@app/access-requests/services/access-request.mock-service';
import { ConfigService } from '@app/shared/services/config';
import { provideHttpCache } from '@ngneat/cashew';
import { ActiveAccessGrantsListComponent } from './active-access-grants-list';

const MockConfigService = {
  auth_url: '/test/auth',
};

describe('ActiveAccessGrantsListComponent', () => {
  let component: ActiveAccessGrantsListComponent;
  let fixture: ComponentFixture<ActiveAccessGrantsListComponent>;
  let accessRequestService: AccessRequestService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ActiveAccessGrantsListComponent],
      providers: [
        { provide: AccessRequestService, useClass: MockAccessRequestService },
        { provide: ConfigService, useValue: MockConfigService },
        provideHttpClient(),
        provideHttpCache(),
      ],
    }).compileComponents();

    accessRequestService = TestBed.inject(AccessRequestService);
    fixture = TestBed.createComponent(ActiveAccessGrantsListComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should fetch the access grants again when refreshed', () => {
    const reload = vitest.spyOn(accessRequestService, 'reloadUserAccessGrants');
    component.refresh();
    expect(reload).toHaveBeenCalledTimes(1);
  });
});
