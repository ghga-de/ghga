/**
 * Test the Access Grant Manager component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ActivatedRoute } from '@angular/router';
import { fakeActivatedRoute } from '@app/../mocks/route';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { AccessGrantManager } from './access-grant-manager';

import { MockAccessRequestService } from '@app/access-requests/services/access-request.mock-service';
import { screen } from '@testing-library/angular';

describe('AccessGrantManager', () => {
  let component: AccessGrantManager;
  let fixture: ComponentFixture<AccessGrantManager>;
  let accessRequestService: AccessRequestService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AccessGrantManager],
      providers: [
        { provide: AccessRequestService, useClass: MockAccessRequestService },
        { provide: ActivatedRoute, useValue: fakeActivatedRoute },
      ],
    }).compileComponents();

    accessRequestService = TestBed.inject(AccessRequestService);
    accessRequestService.reloadAllAccessGrants = vitest.fn();
    fixture = TestBed.createComponent(AccessGrantManager);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should fetch all the access grants again upon initialization', () => {
    expect(accessRequestService.reloadAllAccessGrants).toHaveBeenCalled();
  });

  it('should fetch all the access grants again when the refresh button is used', () => {
    screen.getByRole('button', { name: 'Refresh the access grants' }).click();
    expect(accessRequestService.reloadAllAccessGrants).toHaveBeenCalledTimes(2);
  });
});
