/**
 * Test the Access Grant Manager List component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MockAccessRequestService } from '@app/access-requests/services/access-request.mock-service';
import { AccessRequestService } from '@app/access-requests/services/access-request.service';
import { AccessGrantManagerListComponent } from './access-grant-manager-list.component';

describe('AccessGrantManagerListComponent', () => {
  let component: AccessGrantManagerListComponent;
  let fixture: ComponentFixture<AccessGrantManagerListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [],
      providers: [
        { provide: AccessRequestService, useClass: MockAccessRequestService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AccessGrantManagerListComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
