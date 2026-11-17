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
    size: 2.5 * 1024 ** 3,
    storage_alias: 'TUE01',
    max_size: 10 * 1024 ** 4,
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
  boxRetrievalResults = {
    error: signal<Error | undefined>(undefined),
    isLoading: signal(false),
  };
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
    .map((row) =>
      within(row)
        .getByText(/^Box [A-Z]$/)
        .textContent!.trim(),
    );
}

/**
 * Get the text of the header line about the last change.
 * @returns the text, with the whitespace collapsed
 */
function lastChangeLine(): string {
  return screen
    .getByText(/^\s*(Last changed|No edit history)/)
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

  it('should load the boxes and the order again when it opens', () => {
    expect(uploadBoxService.reloadAllUploadBoxes).toHaveBeenCalledOnce();
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
    expect(row).toHaveTextContent('Tübingen 1 – Open – 2.5 GiB of 10.0 TiB');
    expect(within(row).getByText('2')).toHaveClass('text-right');
    // In the colours of the table
    expect(within(row).getByText('Open')).toHaveClass('text-success');
  });

  it('should show the steward who changed the order last', () => {
    expect(userService.fetcher.load).toHaveBeenCalledWith('doe@test.dev');
    expect(lastChangeLine()).toBe('Last changed by Dr. John Doe on 10 February 2025.');
    expect(screen.getByRole('link', { name: 'Dr. John Doe' })).toHaveAttribute(
      'href',
      '/user-manager/doe@test.dev',
    );
  });

  it('should show the plain ID if the name cannot be loaded', async () => {
    userService.fetcher.resource.error.set(new Error('not found'));
    await result.fixture.whenStable();

    expect(lastChangeLine()).toBe('Last changed by doe@test.dev on 10 February 2025.');
    expect(screen.queryByRole('link')).toBeNull();
  });

  it('should say that the RS changed the order after a repair at startup', async () => {
    uploadBoxService.boxPriority.value.set({
      ...PRIORITY,
      version: 1,
      changed_by: null,
    });
    await result.fixture.whenStable();

    expect(lastChangeLine()).toBe('Last changed automatically on 10 February 2025.');
  });

  it('should say that there is no edit history before the first write', async () => {
    uploadBoxService.boxPriority.value.set({
      version: 0,
      entries: [],
      changed_by: null,
      last_changed: null,
    });
    await result.fixture.whenStable();

    expect(lastChangeLine()).toBe('No edit history yet.');
  });

  it('should describe the move buttons in tooltips', () => {
    expect(
      screen.getByRole('button', { name: 'Move Box B up' }),
    ).toHaveAccessibleDescription('Move up');
    expect(
      screen.getByRole('button', { name: 'Move Box B down' }),
    ).toHaveAccessibleDescription('Move down');
    expect(
      screen.getByRole('button', { name: 'Move Box B to top' }),
    ).toHaveAccessibleDescription('Move to top');
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
    const save = screen.getByRole('button', { name: 'Save order' });
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
    await click('Save order');

    expect(uploadBoxService.saveBoxPriority).toHaveBeenCalledWith(7, [
      'box-b',
      'box-a',
      'box-c',
    ]);
    expect(notifyMock.showSuccess).toHaveBeenCalledWith(
      'Saved the new order. Data Hubs use it from their next batch.',
    );
    expect(done).toHaveBeenCalledOnce();
    expect(lastChangeLine()).toBe('Last changed by Dr. John Doe on 11 February 2025.');
    expect(result.fixture.componentInstance.hasChanges()).toBe(false);
  });

  it('should load the current order if it changed in the meantime', async () => {
    uploadBoxService.saveBoxPriority.mockReturnValue(
      throwError(() => new HttpErrorResponse({ status: 409 })),
    );

    await click('Move Box B up');
    await click('Save order');

    // Once when it opened, once after the conflict
    expect(uploadBoxService.reloadAllUploadBoxes).toHaveBeenCalledTimes(2);
    expect(done).not.toHaveBeenCalled();

    // The reload brings another steward's order
    uploadBoxService.boxPriority.value.set({ ...PRIORITY, version: 8 });
    uploadBoxService.prioritizedUploadBoxes.set([BOXES[2], BOXES[0], BOXES[1]]);
    await result.fixture.whenStable();

    expect(titles()).toEqual(['Box C', 'Box A', 'Box B']);
    expect(
      screen.getByText(/The priority order changed while you were editing/),
    ).toBeVisible();
    expect(screen.getByRole('button', { name: 'Save order' })).toBeDisabled();
  });

  it('should not let the steward move boxes before the boxes have loaded again', async () => {
    uploadBoxService.saveBoxPriority.mockReturnValue(
      throwError(() => new HttpErrorResponse({ status: 409 })),
    );
    await click('Move Box B up');
    await click('Save order');

    // The order arrives before the boxes
    uploadBoxService.boxRetrievalResults.isLoading.set(true);
    uploadBoxService.boxPriority.value.set({ ...PRIORITY, version: 8 });
    uploadBoxService.prioritizedUploadBoxes.set([BOXES[2], BOXES[0], BOXES[1]]);
    await result.fixture.whenStable();
    expect(screen.getByRole('button', { name: 'Move Box A up' })).toBeDisabled();

    uploadBoxService.boxRetrievalResults.isLoading.set(false);
    await result.fixture.whenStable();
    expect(screen.getByRole('button', { name: 'Move Box A up' })).toBeEnabled();
  });

  it.each(['boxes', 'order'])(
    'should show an error if the %s fail to load again after a conflict',
    async (failed) => {
      uploadBoxService.saveBoxPriority.mockReturnValue(
        throwError(() => new HttpErrorResponse({ status: 409 })),
      );
      await click('Move Box B up');
      await click('Save order');

      const error = new HttpErrorResponse({ status: 500 });
      if (failed === 'boxes') {
        uploadBoxService.boxRetrievalResults.error.set(error);
        uploadBoxService.prioritizedUploadBoxes.set([]);
      } else {
        uploadBoxService.boxPriority.error.set(error);
        uploadBoxService.prioritizedUploadBoxes.set(undefined);
      }
      await result.fixture.whenStable();

      expect(
        screen.getByText(/error retrieving the upload boxes or their priority order/),
      ).toBeVisible();
      expect(screen.queryByText(/no boxes that are not archived/)).toBeNull();
      expect(screen.queryByText(/This is the current order/)).toBeNull();
      expect(screen.getByText(/The priority order changed/)).toBeVisible();
      expect(screen.getByRole('button', { name: 'Save order' })).toBeDisabled();
    },
  );

  it('should keep the changes if the save fails', async () => {
    uploadBoxService.saveBoxPriority.mockReturnValue(
      throwError(() => new HttpErrorResponse({ status: 500 })),
    );

    await click('Move Box B up');
    await click('Save order');

    expect(
      screen.getByText('Saving failed. Your changes are kept; please try again.'),
    ).toBeVisible();
    expect(titles()).toEqual(['Box B', 'Box A', 'Box C']);
    expect(screen.getByRole('button', { name: 'Save order' })).toBeEnabled();
    // Only when it opened
    expect(uploadBoxService.reloadAllUploadBoxes).toHaveBeenCalledOnce();
    expect(done).not.toHaveBeenCalled();
  });

  it('should finish on cancel without saving', async () => {
    await click('Move Box B up');
    await click('Cancel');

    expect(done).toHaveBeenCalledOnce();
    expect(uploadBoxService.saveBoxPriority).not.toHaveBeenCalled();
  });

  describe('after a button move', () => {
    let animate: Mock;

    beforeEach(() => {
      // jsdom has no layout and no Web Animations: each row is 50 px high
      vitest
        .spyOn(HTMLElement.prototype, 'getBoundingClientRect')
        .mockImplementation(function (this: HTMLElement) {
          const rows = [...(this.parentElement?.children ?? [])];
          return { top: rows.indexOf(this) * 50 } as DOMRect;
        });
      animate = vitest.fn();
      HTMLElement.prototype.animate = animate;
    });

    afterEach(() => {
      vitest.restoreAllMocks();
      vitest.unstubAllGlobals();
      delete (HTMLElement.prototype as Partial<HTMLElement>).animate;
    });

    it('should slide the rows to their new places in a fixed time', async () => {
      await click('Move Box C to top');

      const offsets = animate.mock.calls.map(([keyframes]) => keyframes[0].transform);
      // Box C comes up from the bottom, Box A and Box B go down one row
      expect(offsets).toEqual([
        'translateY(100px)',
        'translateY(-50px)',
        'translateY(-50px)',
      ]);
      for (const [, options] of animate.mock.calls) {
        expect(options.duration).toBe(200);
      }
    });

    it('should not slide the rows if the user prefers reduced motion', async () => {
      vitest.stubGlobal('matchMedia', (query: string) => ({
        matches: query === '(prefers-reduced-motion: reduce)',
      }));

      await click('Move Box C to top');

      expect(titles()).toEqual(['Box C', 'Box A', 'Box B']);
      expect(animate).not.toHaveBeenCalled();
    });
  });
});
