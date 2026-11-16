/**
 * Test the reorder mode of the Upload Box Manager.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { CdkDragDrop, CdkDropList } from '@angular/cdk/drag-drop';
import { HttpErrorResponse } from '@angular/common/http';
import { signal } from '@angular/core';
import { By } from '@angular/platform-browser';
import { DisplayUser, UserService } from '@app/auth/services/user';
import { Notifier } from '@app/shared/services/notification';
import { ResearchDataUploadBox, UploadBoxState } from '@app/upload/models/box';
import { UploadBoxPriority } from '@app/upload/models/box-priority';
import { UploadBoxService } from '@app/upload/services/upload-box';
import { render, RenderResult, screen, within } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';
import { of, throwError } from 'rxjs';
import type { Mock } from 'vitest';
import { UploadBoxPriorityEditor } from './upload-box-priority-editor';

/**
 * Create an upload box for the tests.
 * @param letter - the letter in the box's ID and title
 * @returns an open upload box
 */
function box(letter: string): ResearchDataUploadBox {
  return {
    id: `box-${letter}`,
    version: 1,
    state: UploadBoxState.open,
    title: `Box ${letter.toUpperCase()}`,
    description: '',
    last_changed: '2025-02-01T09:00:00Z',
    changed_by: 'doe@test.dev',
    file_count: 3,
    size: 0,
    storage_alias: 'TUE01',
    max_size: 1_000_000,
  };
}

const BOXES = ['a', 'b', 'c'].map(box);

const PRIORITY: UploadBoxPriority = {
  version: 7,
  entries: BOXES.map((box) => ({
    research_data_upload_box_id: box.id,
    file_upload_box_id: `file-${box.id}`,
  })),
  changed_by: 'doe@test.dev',
  last_changed: '2025-02-10T14:30:00Z',
};

const STEWARD = { id: 'doe@test.dev', displayName: 'Dr. John Doe' } as DisplayUser;

/**
 * Mock the upload box service as needed by the reorder mode.
 */
class MockUploadBoxService {
  boxPriority = {
    value: signal<UploadBoxPriority>(PRIORITY),
    error: signal<Error | undefined>(undefined),
    isLoading: signal(false),
  };
  prioritizedUploadBoxes = signal<ResearchDataUploadBox[] | undefined>(BOXES);
  getStorageLocationLabel = (storageAlias: string) =>
    storageAlias === 'TUE01' ? 'Tübingen 1' : storageAlias;
  saveBoxPriority = vitest.fn();
  reloadAllUploadBoxes = vitest.fn();
}

/**
 * Mock the user service, which loads the steward who changed the order last.
 */
class MockUserService {
  fetcher = {
    load: vitest.fn(),
    resource: {
      value: signal<DisplayUser | undefined>(STEWARD),
      error: signal<Error | undefined>(undefined),
    },
  };

  /**
   * Return the one user fetcher of this mock.
   * @returns the user fetcher
   */
  createUserFetcher() {
    return this.fetcher;
  }
}

const notifyMock = { showSuccess: vitest.fn() };

/**
 * Get the titles of the boxes in the list, from top to bottom.
 * @returns the box titles
 */
function titles(): string[] {
  return within(screen.getByRole('list', { name: 'Priority order' }))
    .getAllByRole('listitem')
    .map((row) => row.querySelector('strong')?.textContent?.trim() ?? '');
}

/**
 * Get the text of the header line with the version and the last change.
 * @returns the text, with the whitespace collapsed
 */
function versionLine(): string {
  return screen
    .getByText(/^\s*Version/)
    .textContent!.replace(/\s+/g, ' ')
    .trim();
}

describe('UploadBoxPriorityEditor', () => {
  let result: RenderResult<UploadBoxPriorityEditor>;
  let uploadBoxService: MockUploadBoxService;
  let userService: MockUserService;
  let done: Mock<() => void>;

  beforeEach(async () => {
    notifyMock.showSuccess.mockClear();
    uploadBoxService = new MockUploadBoxService();
    userService = new MockUserService();

    result = await render(UploadBoxPriorityEditor, {
      providers: [
        { provide: UploadBoxService, useValue: uploadBoxService },
        { provide: UserService, useValue: userService },
        { provide: Notifier, useValue: notifyMock },
      ],
    });
    done = vitest.fn<() => void>();
    result.fixture.componentInstance.done.subscribe(done);
  });

  /**
   * Click a button and wait for the page to update.
   * @param name - the accessible name of the button
   */
  async function click(name: string | RegExp): Promise<void> {
    await userEvent.click(screen.getByRole('button', { name }));
    await result.fixture.whenStable();
  }

  it('should list the boxes in the loaded order', () => {
    expect(titles()).toEqual(['Box A', 'Box B', 'Box C']);
    const row = screen.getAllByRole('listitem')[1];
    expect(row).toHaveTextContent('2');
    expect(row).toHaveTextContent('Tübingen 1 – Open – 3 files');
  });

  it('should show the version and the steward who changed the order last', () => {
    expect(userService.fetcher.load).toHaveBeenCalledWith('doe@test.dev');
    expect(versionLine()).toBe(
      'Version 7. Last changed by Dr. John Doe on 10 February 2025.',
    );
    expect(screen.getByRole('link', { name: 'Dr. John Doe' })).toHaveAttribute(
      'href',
      '/user-manager/doe@test.dev',
    );
  });

  it('should show the plain ID if the name cannot be loaded', async () => {
    userService.fetcher.resource.error.set(new Error('not found'));
    await result.fixture.whenStable();

    expect(versionLine()).toBe(
      'Version 7. Last changed by doe@test.dev on 10 February 2025.',
    );
    expect(screen.queryByRole('link')).toBeNull();
  });

  it('should say that the RS changed the order after a repair at startup', async () => {
    uploadBoxService.boxPriority.value.set({
      ...PRIORITY,
      version: 1,
      changed_by: null,
    });
    await result.fixture.whenStable();

    expect(versionLine()).toBe(
      'Version 1. Last changed automatically on 10 February 2025.',
    );
  });

  it('should say that there is no edit history before the first write', async () => {
    uploadBoxService.boxPriority.value.set({
      version: 0,
      entries: [],
      changed_by: null,
      last_changed: null,
    });
    await result.fixture.whenStable();

    expect(versionLine()).toBe('Version 0. No edit history yet.');
  });

  it('should move a box with its buttons', async () => {
    await click('Move Box C up');
    expect(titles()).toEqual(['Box A', 'Box C', 'Box B']);

    await click('Move Box A down');
    expect(titles()).toEqual(['Box C', 'Box A', 'Box B']);

    await click('Move Box B to top');
    expect(titles()).toEqual(['Box B', 'Box C', 'Box A']);

    expect(screen.getByRole('button', { name: 'Move Box B up' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Move Box B to top' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Move Box A down' })).toBeDisabled();
    expect(
      screen.getByText('You have unsaved changes to the priority order.'),
    ).toBeVisible();
    expect(result.fixture.componentInstance.hasChanges()).toBe(true);
  });

  it('should move a box to where it is dropped', async () => {
    const dropList = result.fixture.debugElement
      .query(By.directive(CdkDropList))
      .injector.get(CdkDropList);
    dropList.dropped.emit({
      previousIndex: 2,
      currentIndex: 0,
    } as CdkDragDrop<unknown>);
    await result.fixture.whenStable();

    expect(titles()).toEqual(['Box C', 'Box A', 'Box B']);
  });

  it('should disable saving when the order is back to the loaded one', async () => {
    const save = screen.getByRole('button', { name: 'Save priority' });
    expect(save).toBeDisabled();

    await click('Move Box B up');
    expect(save).toBeEnabled();

    await click('Move Box B down');
    expect(titles()).toEqual(['Box A', 'Box B', 'Box C']);
    expect(save).toBeDisabled();
    expect(screen.queryByText(/unsaved changes/)).toBeNull();
    expect(result.fixture.componentInstance.hasChanges()).toBe(false);
  });

  it('should save the new order with the loaded version', async () => {
    const savedPriority: UploadBoxPriority = {
      ...PRIORITY,
      version: 8,
      entries: [PRIORITY.entries[1], PRIORITY.entries[0], PRIORITY.entries[2]],
      last_changed: '2025-02-11T09:00:00Z',
    };
    uploadBoxService.saveBoxPriority.mockImplementation(() => {
      uploadBoxService.boxPriority.value.set(savedPriority);
      uploadBoxService.prioritizedUploadBoxes.set([BOXES[1], BOXES[0], BOXES[2]]);
      return of(savedPriority);
    });

    await click('Move Box B up');
    await click('Save priority');

    expect(uploadBoxService.saveBoxPriority).toHaveBeenCalledWith(7, [
      'box-b',
      'box-a',
      'box-c',
    ]);
    expect(notifyMock.showSuccess).toHaveBeenCalledWith(
      'Saved as version 8. Data Hubs use it from their next batch.',
    );
    expect(done).toHaveBeenCalledOnce();
    expect(versionLine()).toBe(
      'Version 8. Last changed by Dr. John Doe on 11 February 2025.',
    );
    expect(result.fixture.componentInstance.hasChanges()).toBe(false);
  });

  it('should load the current order if it changed in the meantime', async () => {
    uploadBoxService.saveBoxPriority.mockReturnValue(
      throwError(() => new HttpErrorResponse({ status: 409 })),
    );

    await click('Move Box B up');
    await click('Save priority');

    expect(uploadBoxService.reloadAllUploadBoxes).toHaveBeenCalledOnce();
    expect(done).not.toHaveBeenCalled();

    // The reload brings another steward's order
    uploadBoxService.boxPriority.value.set({ ...PRIORITY, version: 8 });
    uploadBoxService.prioritizedUploadBoxes.set([BOXES[2], BOXES[0], BOXES[1]]);
    await result.fixture.whenStable();

    expect(titles()).toEqual(['Box C', 'Box A', 'Box B']);
    expect(
      screen.getByText(/The priority order changed while you were editing/),
    ).toBeVisible();
    expect(screen.getByRole('button', { name: 'Save priority' })).toBeDisabled();
  });

  it('should keep the changes if the save fails', async () => {
    uploadBoxService.saveBoxPriority.mockReturnValue(
      throwError(() => new HttpErrorResponse({ status: 500 })),
    );

    await click('Move Box B up');
    await click('Save priority');

    expect(
      screen.getByText('Saving failed. Your changes are kept; please try again.'),
    ).toBeVisible();
    expect(titles()).toEqual(['Box B', 'Box A', 'Box C']);
    expect(screen.getByRole('button', { name: 'Save priority' })).toBeEnabled();
    expect(uploadBoxService.reloadAllUploadBoxes).not.toHaveBeenCalled();
    expect(done).not.toHaveBeenCalled();
  });

  it('should finish on cancel without saving', async () => {
    await click('Move Box B up');
    await click('Cancel');

    expect(done).toHaveBeenCalledOnce();
    expect(uploadBoxService.saveBoxPriority).not.toHaveBeenCalled();
  });
});
