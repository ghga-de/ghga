/**
 * Test the Access Grant Manager Filter component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AccessGrantStatus } from '@app/access-requests/models/access-requests';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { MockAccessRequestService } from '@app/access-requests/services/access-request.mock-service';
import { screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';
import { AccessGrantManagerFilter } from './access-grant-manager-filter';

describe('AccessGrantManagerFilter', () => {
  let component: AccessGrantManagerFilter;
  let fixture: ComponentFixture<AccessGrantManagerFilter>;
  let setFilter: ReturnType<typeof vitest.spyOn>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AccessGrantManagerFilter],
      providers: [
        { provide: AccessRequestService, useClass: MockAccessRequestService },
      ],
    }).compileComponents();

    const service = TestBed.inject(AccessRequestService);
    setFilter = vitest.spyOn(service, 'setAllAccessGrantsFilter');
    fixture = TestBed.createComponent(AccessGrantManagerFilter);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  /**
   * Get the filter the component sent last
   * @returns the last filter
   */
  function lastFilter() {
    return setFilter.mock.lastCall![0];
  }

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should set the filter after typing a name and a dataset ID', async () => {
    await userEvent.type(screen.getByRole('textbox', { name: 'Name or Email' }), 'Doe');
    await userEvent.type(screen.getByRole('textbox', { name: 'Dataset ID' }), 'GHGAD1');
    await fixture.whenStable();

    expect(lastFilter()).toMatchObject({ user: 'Doe', dataset_id: 'GHGAD1' });
  });

  it('should set the filter after selecting a grant status', async () => {
    await userEvent.click(screen.getByRole('combobox', { name: 'All grant statuses' }));
    await userEvent.click(screen.getByRole('option', { name: 'Expired' }));
    await fixture.whenStable();

    expect(lastFilter()).toMatchObject({ status: AccessGrantStatus.expired });
  });

  it('should clear the filter with the remove buttons', async () => {
    const textbox = screen.getByRole('textbox', { name: 'Name or Email' });
    await userEvent.type(textbox, 'Doe');
    await userEvent.click(screen.getByRole('combobox', { name: 'All grant statuses' }));
    await userEvent.click(screen.getByRole('option', { name: 'Active' }));
    await userEvent.click(
      screen.getByRole('button', { name: 'Remove filter for name and email' }),
    );
    await userEvent.click(
      screen.getByRole('button', { name: 'Remove filter for grant status' }),
    );
    await fixture.whenStable();

    expect(lastFilter().user).toBeFalsy();
    expect(lastFilter().status).toBeUndefined();
    expect(textbox).toHaveValue('');
  });
});
