/**
 * Test the Access Request Manager component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AccessRequestService } from '@app/access-requests/services/access-request';
import { AccessRequestManagerComponent } from './access-request-manager';

import { screen } from '@testing-library/angular';
import { AccessRequestManagerFilterComponent } from '../access-request-manager-filter/access-request-manager-filter';
import { AccessRequestManagerListComponent } from '../access-request-manager-list/access-request-manager-list';

/**
 * Mock the access request service as needed by the access request manager
 */
const mockAccessRequestService = {
  loadAllAccessRequests: jest.fn(),
};

describe('AccessRequestManagerComponent', () => {
  let component: AccessRequestManagerComponent;
  let fixture: ComponentFixture<AccessRequestManagerComponent>;
  let accessRequestService: AccessRequestService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AccessRequestManagerComponent],
      providers: [
        { provide: AccessRequestService, useValue: mockAccessRequestService },
      ],
    })
      .overrideComponent(AccessRequestManagerComponent, {
        remove: {
          imports: [
            AccessRequestManagerFilterComponent,
            AccessRequestManagerListComponent,
          ],
        },
      })
      .compileComponents();

    fixture = TestBed.createComponent(AccessRequestManagerComponent);
    accessRequestService = TestBed.inject(AccessRequestService);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should show the proper heading', () => {
    const heading = screen.getByRole('heading', { level: 1 });
    expect(heading).toHaveTextContent('Access Request Management');
  });

  it('should load all the access requests upon initialization', () => {
    expect(accessRequestService.loadAllAccessRequests).toHaveBeenCalled();
  });
});
