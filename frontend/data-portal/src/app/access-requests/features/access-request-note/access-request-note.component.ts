/**
 * This component displays a note for an access request.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, computed, Input } from '@angular/core';
import {
  AccessRequest,
  NotesTypeSelection,
} from '@app/access-requests/models/access-requests';

/**
 * This is a so-called "dumb" component that displays a note for an access request.
 */
@Component({
  selector: 'app-access-request-note',
  imports: [],
  templateUrl: './access-request-note.component.html',
})
export class AccessRequestNoteComponent {
  @Input() request!: AccessRequest;
  @Input() noteTypes!: NotesTypeSelection;
  @Input() showAsTable: boolean = false;

  showInternalNote = computed(() => {
    return (
      this.request.internal_note &&
      (this.noteTypes == NotesTypeSelection.internalNote ||
        this.noteTypes == NotesTypeSelection.both)
    );
  });

  showNoteToRequester = computed(() => {
    return (
      this.request.note_to_requester &&
      (this.noteTypes == NotesTypeSelection.noteToRequester ||
        this.noteTypes == NotesTypeSelection.both)
    );
  });
}
