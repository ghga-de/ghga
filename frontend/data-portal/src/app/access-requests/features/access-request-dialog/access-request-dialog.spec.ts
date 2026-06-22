/**
 * Tests for the Content of the data access request dialog.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { provideNativeDateAdapter } from '@angular/material/core';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { ConfigService } from '@app/shared/services/config';
import { localDateToContractIsoUtc } from '@app/shared/utils/date-formats';
import { AccessRequestDialogComponent } from './access-request-dialog';

const mockDialogRef = {
  close: vitest.fn(),
};

const mockDialogData = {
  datasetID: 'GHGAD12345678901234',
  email: 'user@example.test',
  description: '',
  fromDate: undefined,
  untilDate: undefined,
  userId: 'user-1',
};

// ConfigService mock (camelCase getters); the component only reads these.
const mockConfig = {
  accessUpfrontMaxDays: 180,
  accessGrantMinDays: 7,
  accessGrantMaxDays: 730,
  defaultAccessDurationDays: 365,
};

describe('AccessRequestDialogComponent', () => {
  let component: AccessRequestDialogComponent;
  let fixture: ComponentFixture<AccessRequestDialogComponent>;

  beforeEach(async () => {
    mockDialogRef.close.mockReset();
    await TestBed.configureTestingModule({
      imports: [AccessRequestDialogComponent, MatDialogModule],
      providers: [
        provideNativeDateAdapter(),
        { provide: MatDialogRef, useValue: mockDialogRef },
        { provide: MAT_DIALOG_DATA, useValue: mockDialogData },
        { provide: ConfigService, useValue: mockConfig },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AccessRequestDialogComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('datasetID', 'GHGAD12345678901234');
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should submit with ISO UTC dates based on service-contract day boundaries', () => {
    const fromDate = new Date(component.todayMidnight);
    const untilDate = new Date(component.todayMidnight);
    untilDate.setDate(untilDate.getDate() + mockConfig.accessGrantMinDays);
    // The component treats end dates as the end of the day (23:59:59.999), so the
    // earliest valid until date is the end of fromDate + accessGrantMinDays.
    untilDate.setHours(23, 59, 59, 999);

    component.updateUntilRangeForFromValue(fromDate);
    component.updateFromRangeForUntilValue(untilDate);
    (
      component as unknown as {
        model: {
          set: (value: {
            description: string;
            fromDate: Date | null;
            untilDate: Date | null;
            email: string;
          }) => void;
        };
      }
    ).model.set({
      description: 'Need access for analysis',
      fromDate,
      untilDate,
      email: 'user@example.test',
    });

    component.submit();

    expect(mockDialogRef.close).toHaveBeenCalledTimes(1);
    const payload = mockDialogRef.close.mock.calls[0][0];
    expect(payload.fromDate.toISOString()).toBe(localDateToContractIsoUtc(fromDate));
    expect(payload.untilDate.toISOString()).toBe(
      localDateToContractIsoUtc(untilDate, true),
    );
  });
});
