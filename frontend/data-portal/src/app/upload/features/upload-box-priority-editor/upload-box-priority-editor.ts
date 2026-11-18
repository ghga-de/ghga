/**
 * Reorder mode of the Upload Box Manager, for changing the priority order.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import {
  CdkDrag,
  CdkDragDrop,
  CdkDragHandle,
  CdkDragPlaceholder,
  CdkDragPreview,
  CdkDropList,
  moveItemInArray,
} from '@angular/cdk/drag-drop';
import { DatePipe as CommonDatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import {
  afterNextRender,
  Component,
  computed,
  DestroyRef,
  effect,
  ElementRef,
  inject,
  Injector,
  linkedSignal,
  OnInit,
  output,
  signal,
  viewChild,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { MatTooltip } from '@angular/material/tooltip';
import { RouterLink } from '@angular/router';
import { DisplayUser, UserService } from '@app/auth/services/user';
import { Capitalise } from '@app/shared/pipes/capitalise-pipe';
import { DatePipe } from '@app/shared/pipes/date-pipe';
import { ParseBytes } from '@app/shared/pipes/parse-bytes-pipe';
import { Notifier } from '@app/shared/services/notification';
import {
  DEFAULT_TIME_ZONE,
  FRIENDLY_DATE_TIME_FORMAT,
} from '@app/shared/utils/date-formats';
import { UploadBoxStateClass } from '@app/upload/models/box';
import { UploadBoxService } from '@app/upload/services/upload-box';

/** How long a moved row stays highlighted, in milliseconds */
const HIGHLIGHT_DURATION = 1500;

/**
 * How long the rows take to slide to their new places after a button move, in
 * milliseconds. Fixed, so that moving to the top of a long list is not slower.
 */
const MOVE_ANIMATION_DURATION = 200;

/** The move buttons of a row */
type MoveAction = 'up' | 'down' | 'top';

/**
 * The list of all upload boxes that are not archived, in priority order, where
 * the steward moves boxes by dragging them or with their buttons, and saves the
 * new order.
 */
@Component({
  selector: 'app-upload-box-priority-editor',
  imports: [
    CdkDrag,
    CdkDragHandle,
    CdkDragPlaceholder,
    CdkDragPreview,
    CdkDropList,
    Capitalise,
    DatePipe,
    MatButtonModule,
    MatIcon,
    MatTooltip,
    ParseBytes,
    RouterLink,
  ],
  templateUrl: './upload-box-priority-editor.html',
  styleUrl: './upload-box-priority-editor.scss',
  providers: [CommonDatePipe],
})
export class UploadBoxPriorityEditor implements OnInit {
  #uploadBoxService = inject(UploadBoxService);
  #userService = inject(UserService);
  #notifier = inject(Notifier);
  #host = inject<ElementRef<HTMLElement>>(ElementRef);
  #injector = inject(Injector);

  /** Emits after Cancel and after a successful save */
  done = output<void>();

  protected readonly friendlyDateTimeFormat = FRIENDLY_DATE_TIME_FORMAT;
  protected readonly timeZone = DEFAULT_TIME_ZONE;

  private heading = viewChild.required<ElementRef<HTMLElement>>('heading');

  /** The loaded priority order, undefined if it failed to load */
  protected priority = computed(() =>
    this.#uploadBoxService.boxPriority.error()
      ? undefined
      : this.#uploadBoxService.boxPriority.value(),
  );

  /** The boxes in the loaded order */
  #loadedBoxes = computed(() => this.#uploadBoxService.prioritizedUploadBoxes() ?? []);

  /** The boxes in the steward's order, reset to the loaded order when it loads again */
  #order = linkedSignal(() => this.#loadedBoxes());

  /** Whether the steward's order differs from the loaded one */
  hasChanges = computed(() => {
    const loadedBoxes = this.#loadedBoxes();
    return this.#order().some((box, index) => box.id !== loadedBoxes[index]?.id);
  });

  protected saving = signal(false);

  /**
   * Whether the order can't be changed right now, while saving or loading.
   * Both the boxes and the order must have loaded, since each of them resets
   * the steward's order when it arrives.
   */
  protected busy = computed(
    () =>
      this.saving() ||
      this.#uploadBoxService.boxRetrievalResults.isLoading() ||
      this.#uploadBoxService.boxPriority.isLoading(),
  );

  /** Whether the boxes or their order failed to load */
  protected loadFailed = computed(
    () =>
      !!this.#uploadBoxService.boxRetrievalResults.error() ||
      !!this.#uploadBoxService.boxPriority.error(),
  );

  protected canSave = computed(
    () => this.hasChanges() && !this.busy() && !!this.priority(),
  );

  #saveError = signal<'conflict' | 'failed' | undefined>(undefined);

  /** The message about the changes and the last save */
  protected status = computed(() => {
    switch (this.#saveError()) {
      case 'conflict':
        return this.loadFailed()
          ? 'The priority order changed while you were editing.'
          : 'The priority order changed while you were editing. ' +
              'This is the current order; please make your change again.';
      case 'failed':
        return 'Saving failed. Your changes are kept; please try again.';
    }
    return this.hasChanges() ? 'You have unsaved changes to the priority order.' : '';
  });

  protected statusIsError = computed(() => this.#saveError() !== undefined);

  #highlightedId = signal<string | undefined>(undefined);
  #highlightTimer: ReturnType<typeof setTimeout> | undefined;

  /** The rows of the list, with what the template shows of each box */
  protected rows = computed(() => {
    const order = this.#order();
    const highlightedId = this.#highlightedId();
    return order.map((box, index) => ({
      box,
      index,
      position: index + 1,
      storageLabel: this.#uploadBoxService.getStorageLocationLabel(box.storage_alias),
      stateClass: UploadBoxStateClass[box.state],
      highlighted: box.id === highlightedId,
      isFirst: index === 0,
      isLast: index === order.length - 1,
    }));
  });

  #reorderedByFetcher = this.#userService.createUserFetcher();

  #loadReorderedByEffect = effect(() => {
    const reorderedById = this.priority()?.reordered_by;
    if (reorderedById) this.#reorderedByFetcher.load(reorderedById);
  });

  /**
   * The data steward who last saved a new order, undefined while loading, null on
   * error. Unlike `changed_by`, creating, archiving or deleting a box keeps it.
   */
  protected reorderedBy = computed<DisplayUser | null | undefined>(() => {
    const reorderedById = this.priority()?.reordered_by;
    if (!reorderedById) return undefined;
    const reorderedByResource = this.#reorderedByFetcher.resource;
    if (reorderedByResource.error()) return null;
    const reorderedByUser = reorderedByResource.value();
    return reorderedByUser?.id === reorderedById ? reorderedByUser : undefined;
  });

  constructor() {
    inject(DestroyRef).onDestroy(() => clearTimeout(this.#highlightTimer));
  }

  /**
   * Load the boxes and their order again, so that the steward starts from the
   * current order rather than learning about a newer one only when saving. The
   * focus moves to the heading, since opening reorder mode removed Change order.
   */
  ngOnInit(): void {
    this.#uploadBoxService.reloadAllUploadBoxes();
    afterNextRender(() => this.heading().nativeElement.focus(), {
      injector: this.#injector,
    });
  }

  /**
   * Move a box with one of its buttons. The rows slide to their new places, and
   * the focus stays on that button, or on another button of the row if the move
   * disabled it.
   * @param index - the position of the box in the list, starting at 0
   * @param action - the button that was used
   */
  protected moveWithButton(index: number, action: MoveAction): void {
    const boxId = this.#order()[index].id;
    const target = { up: index - 1, down: index + 1, top: 0 }[action];
    const oldTops = this.#rowTops();
    this.#move(index, target);
    afterNextRender(
      () => {
        this.#slideRows(oldTops);
        const row = this.#host.nativeElement.querySelector(`[data-box-id="${boxId}"]`);
        const button =
          row?.querySelector<HTMLButtonElement>(`[data-action="${action}"]:enabled`) ??
          row?.querySelector<HTMLButtonElement>('button:enabled');
        button?.focus();
      },
      { injector: this.#injector },
    );
  }

  /**
   * Get where each row is on the screen.
   * @returns the top of each row, by box ID
   */
  #rowTops(): Map<string, number> {
    const rows =
      this.#host.nativeElement.querySelectorAll<HTMLElement>('[data-box-id]');
    return new Map(
      [...rows].map((row) => [row.dataset['boxId']!, row.getBoundingClientRect().top]),
    );
  }

  /**
   * Slide the rows that moved from their old places to their new ones (FLIP),
   * unless the user prefers reduced motion.
   * @param oldTops - the top of each row before the move, by box ID
   */
  #slideRows(oldTops: Map<string, number>): void {
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches) return;
    const rows =
      this.#host.nativeElement.querySelectorAll<HTMLElement>('[data-box-id]');
    for (const row of rows) {
      const oldTop = oldTops.get(row.dataset['boxId']!);
      if (oldTop === undefined || typeof row.animate !== 'function') continue;
      const offset = oldTop - row.getBoundingClientRect().top;
      if (!offset) continue;
      row.animate([{ transform: `translateY(${offset}px)` }, { transform: 'none' }], {
        duration: MOVE_ANIMATION_DURATION,
        easing: 'ease-out',
      });
    }
  }

  /**
   * Move a box to where the steward dropped it.
   * @param event - the drop event of the list
   */
  protected drop(event: CdkDragDrop<unknown>): void {
    this.#move(event.previousIndex, event.currentIndex);
  }

  /**
   * Move a box in the steward's order and highlight it for a moment.
   * @param from - the position of the box, starting at 0
   * @param to - the new position of the box
   */
  #move(from: number, to: number): void {
    if (from === to) return;
    const order = [...this.#order()];
    moveItemInArray(order, from, to);
    this.#order.set(order);
    this.#saveError.set(undefined);
    clearTimeout(this.#highlightTimer);
    this.#highlightedId.set(order[to].id);
    this.#highlightTimer = setTimeout(
      () => this.#highlightedId.set(undefined),
      HIGHLIGHT_DURATION,
    );
  }

  /** Throw away the changes. */
  protected cancel(): void {
    this.done.emit();
  }

  /**
   * Save the steward's order. If the order changed in the meantime, load the
   * current order, so that the steward can make the change again.
   */
  protected save(): void {
    const priority = this.priority();
    if (!priority || !this.canSave()) return;
    this.saving.set(true);
    this.#saveError.set(undefined);
    const boxIds = this.#order().map((box) => box.id);
    this.#uploadBoxService.saveBoxPriority(priority.version, boxIds).subscribe({
      next: () => {
        this.saving.set(false);
        this.#notifier.showSuccess(
          'Saved the new order. Data Hubs use it from their next batch.',
        );
        this.done.emit();
      },
      error: (error: unknown) => {
        this.saving.set(false);
        if (error instanceof HttpErrorResponse && error.status === 409) {
          this.#saveError.set('conflict');
          this.#uploadBoxService.reloadAllUploadBoxes();
        } else {
          this.#saveError.set('failed');
        }
      },
    });
  }
}
