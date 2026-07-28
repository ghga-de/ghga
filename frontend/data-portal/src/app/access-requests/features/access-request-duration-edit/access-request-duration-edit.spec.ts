/**
 * Test the Access Request Duration Editor component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideNativeDateAdapter } from '@angular/material/core';

import { AccessRequestDurationEditComponent } from './access-request-duration-edit';

import { accessRequests } from '@app/../mocks/data';
import { AccessRequestStatus } from '@app/access-requests/models/access-requests';
import { ConfigService } from '@app/shared/services/config';
import { localDateToContractIsoUtc } from '@app/shared/utils/date-formats';

interface DurationEditInternals {
  formModel: {
    (): { fromDate: Date | null; untilDate: Date | null };
    set: (value: { fromDate: Date | null; untilDate: Date | null }) => void;
  };
}

/**
 * Read the protected form model of the component under test.
 * @param component - the component under test
 * @returns the current form model
 */
function getFormModel(component: AccessRequestDurationEditComponent) {
  return (component as unknown as DurationEditInternals).formModel();
}

/**
 * Overwrite the protected form model of the component under test.
 * @param component - the component under test
 * @param fromDate - the start date to set
 * @param untilDate - the end date to set
 */
function setFormModel(
  component: AccessRequestDurationEditComponent,
  fromDate: Date | null,
  untilDate: Date | null,
): void {
  (component as unknown as DurationEditInternals).formModel.set({
    fromDate,
    untilDate,
  });
}

/**
 * Mock the config service as needed by the access request duration edit component
 */
class MockConfigService {
  accessGrantMaxDays = 730;
  accessGrantMaxExtend = 5;
  defaultAccessDurationDays = 365;
}

describe('AccessRequestDurationEditComponent', () => {
  let component: AccessRequestDurationEditComponent;
  let fixture: ComponentFixture<AccessRequestDurationEditComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [
        provideNativeDateAdapter(),
        { provide: ConfigService, useClass: MockConfigService },
      ],
      imports: [AccessRequestDurationEditComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(AccessRequestDurationEditComponent);
    fixture.componentRef.setInput('request', accessRequests[0]);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should emit ISO UTC date strings with service-contract day boundaries on save', () => {
    const request = {
      ...accessRequests[0],
      status: AccessRequestStatus.pending,
      access_starts: '2025-01-01T00:00:00.000Z',
      access_ends: '2025-01-08T23:59:59.999Z',
    };
    fixture.componentRef.setInput('request', request);
    fixture.detectChanges();

    const fromDate = new Date(2025, 7, 1);
    const untilDate = new Date(2025, 7, 8);

    let emitted: Map<string, string> | undefined;
    component.saved.subscribe((value) => {
      emitted = value as Map<string, string>;
    });

    component.open();
    setFormModel(component, fromDate, untilDate);
    component.save();

    expect(emitted).toBeDefined();
    expect(emitted?.get('access_starts')).toBe(localDateToContractIsoUtc(fromDate));
    expect(emitted?.get('access_ends')).toBe(
      localDateToContractIsoUtc(untilDate, true),
    );
  });

  it('should not consider re-selecting the same dates a modification', () => {
    component.open();
    const { fromDate, untilDate } = getFormModel(component);

    // pick the very same dates again, which yields new Date objects
    component.onDateSelected(new Date(fromDate!), true);
    component.onDateSelected(new Date(untilDate!), false);

    expect(component.isModified()).toBe(false);
  });

  it('should report pending edits again after a cancelled edit', async () => {
    const edits: boolean[] = [];
    component.edited.subscribe(([, edited]) => edits.push(edited));

    const laterDate = new Date(getFormModel(component).untilDate!);
    laterDate.setDate(laterDate.getDate() - 1);

    component.open();
    component.onDateSelected(laterDate, false);
    await fixture.whenStable();
    expect(component.isModified()).toBe(true);

    component.cancel();
    await fixture.whenStable();
    expect(component.isModified()).toBe(false);

    component.open();
    component.onDateSelected(laterDate, false);
    await fixture.whenStable();

    expect(component.isModified()).toBe(true);
    expect(edits).toEqual([true, false, true]);
  });

  it('should restore only the cleared date to its default', () => {
    component.open();
    const initial = getFormModel(component);
    const changedFrom = new Date(initial.fromDate!);
    changedFrom.setDate(changedFrom.getDate() + 1);
    component.onDateSelected(changedFrom, true);

    // clearing the end date must not touch the start date
    component.onDateSelected(null as unknown as Date, false);

    const current = getFormModel(component);
    expect(current.fromDate?.getTime()).toBe(changedFrom.getTime());
    expect(current.untilDate?.getTime()).toBe(initial.untilDate?.getTime());
  });
});
