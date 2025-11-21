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

    fixture = TestBed.createComponent(ActiveAccessGrantsListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
