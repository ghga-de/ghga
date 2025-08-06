/**
 * Test the Access Grant Manager Details component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ActivatedRoute } from '@angular/router';
import { accessGrants } from '@app/../mocks/data';
import { MockAccessRequestService } from '@app/access-requests/services/access-request.mock-service';
import { AccessRequestService } from '@app/access-requests/services/access-request.service';
import { AccessGrantManagerDetailsComponent } from './access-grant-manager-details.component';

describe('AccessGrantManagerDetailsComponent', () => {
  let component: AccessGrantManagerDetailsComponent;
  let fixture: ComponentFixture<AccessGrantManagerDetailsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AccessGrantManagerDetailsComponent],
      providers: [
        { provide: AccessRequestService, useClass: MockAccessRequestService },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: new Map() } } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AccessGrantManagerDetailsComponent);
    fixture.componentRef.setInput('id', accessGrants[0].id);
    component = fixture.componentInstance;

    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
