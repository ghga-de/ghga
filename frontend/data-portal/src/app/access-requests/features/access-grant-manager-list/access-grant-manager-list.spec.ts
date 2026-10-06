/**
 * Test the Access Grant Manager List component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { accessGrants } from '@app/../mocks/data';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { MockAccessRequestService } from '@app/access-requests/services/access-request.mock-service';
import { render, RenderResult, screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';
import { AccessGrantManagerListComponent } from './access-grant-manager-list';

/**
 * Stand-in for the access grant details page the list navigates to
 */
@Component({ template: '' })
class GrantDetailsStubComponent {}

describe('AccessGrantManagerListComponent', () => {
  let result: RenderResult<AccessGrantManagerListComponent>;

  beforeEach(async () => {
    result = await render(AccessGrantManagerListComponent, {
      providers: [
        { provide: AccessRequestService, useClass: MockAccessRequestService },
      ],
      routes: [
        { path: 'access-grant-manager/:id', component: GrantDetailsStubComponent },
      ],
    });
  });

  it('should create', () => {
    expect(result.fixture.componentInstance).toBeTruthy();
    expect(
      screen.getAllByRole('link', { name: accessGrants[0].dataset_id })[0],
    ).toHaveAttribute('href', `/dataset/${accessGrants[0].dataset_id}`);
  });

  it('should navigate to the details of a grant', async () => {
    const [details] = screen.getAllByRole('button', { name: 'View user details' });
    await userEvent.click(details);
    await result.fixture.whenStable();
    expect(TestBed.inject(Router).url).toBe(
      `/access-grant-manager/${accessGrants[0].id}`,
    );
  });
});
