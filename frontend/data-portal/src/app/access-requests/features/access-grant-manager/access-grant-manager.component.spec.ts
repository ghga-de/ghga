/**
 * Test the Access Grant Manager component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AccessRequestService } from '@app/access-requests/services/access-request.service';
import { AccessGrantManagerComponent } from './access-grant-manager.component';

import { MockAccessRequestService } from '@app/access-requests/services/access-request.mock-service';
import { AccessGrantManagerFilterComponent } from '../access-grant-manager-filter/access-grant-manager-filter.component';
import { AccessGrantManagerListComponent } from '../access-grant-manager-list/access-grant-manager-list.component';

describe('AccessGrantManagerComponent', () => {
  let component: AccessGrantManagerComponent;
  let fixture: ComponentFixture<AccessGrantManagerComponent>;
  let accessRequestService: AccessRequestService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AccessGrantManagerComponent],
      providers: [
        { provide: AccessRequestService, useClass: MockAccessRequestService },
      ],
    })
      .overrideComponent(AccessGrantManagerComponent, {
        remove: {
          imports: [AccessGrantManagerFilterComponent, AccessGrantManagerListComponent],
        },
      })
      .compileComponents();

    fixture = TestBed.createComponent(AccessGrantManagerComponent);
    accessRequestService = TestBed.inject(AccessRequestService);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
