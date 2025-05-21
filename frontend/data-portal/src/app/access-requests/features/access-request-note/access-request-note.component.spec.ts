/**
 * Test the Access Request Note component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AccessRequestNoteComponent } from './access-request-note.component';

import { accessRequests } from '@app/../mocks/data';
import { NotesTypeSelection } from '@app/access-requests/models/access-requests';

describe('AccessRequestNoteComponent', () => {
  let component: AccessRequestNoteComponent;
  let empty_fixture: ComponentFixture<AccessRequestNoteComponent>;
  let fixture_with_one_note: ComponentFixture<AccessRequestNoteComponent>;
  let fixture_with_two_notes: ComponentFixture<AccessRequestNoteComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AccessRequestNoteComponent],
      providers: [],
    }).compileComponents();

    empty_fixture = TestBed.createComponent(AccessRequestNoteComponent);
    empty_fixture.componentRef.setInput('request', accessRequests[0]);
    empty_fixture.componentRef.setInput('noteTypes', NotesTypeSelection.both);
    fixture_with_one_note = TestBed.createComponent(AccessRequestNoteComponent);
    fixture_with_one_note.componentRef.setInput('request', accessRequests[1]);
    fixture_with_one_note.componentRef.setInput(
      'noteTypes',
      NotesTypeSelection.noteToRequester,
    );
    fixture_with_two_notes = TestBed.createComponent(AccessRequestNoteComponent);
    fixture_with_two_notes.componentRef.setInput('request', accessRequests[1]);
    fixture_with_two_notes.componentRef.setInput('noteTypes', NotesTypeSelection.both);
    component = empty_fixture.componentInstance;
    await empty_fixture.whenStable();
    await fixture_with_one_note.whenStable();
    await fixture_with_two_notes.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should not show either note', () => {
    const compiled = empty_fixture.nativeElement as HTMLElement;
    const text = compiled.textContent;
    expect(text).not.toContain('Note:');
  });

  it('should only show the note to the requester', () => {
    const compiled = fixture_with_one_note.nativeElement as HTMLElement;
    const text = compiled.textContent;
    expect(text).not.toContain('Internal note:');
    expect(text).toContain('Note:');
  });

  it('should show both notes', () => {
    const compiled = fixture_with_two_notes.nativeElement as HTMLElement;
    const text = compiled.textContent;
    expect(text).toContain('Internal note:');
    expect(text).toContain('This is a note to the requester.');
  });
});
