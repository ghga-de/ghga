/**
 * Tests for shared confirmation dialog service
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { TestBed } from '@angular/core/testing';

import { MatDialog } from '@angular/material/dialog';
import { of } from 'rxjs';
import { ConfirmDialogComponent } from '../ui/confirm-dialog/confirm-dialog';
import { ConfirmationService } from './confirmation';

describe('ConfirmationService', () => {
  let service: ConfirmationService;
  const matDialogMock = {
    open: jest.fn().mockReturnValue({
      afterClosed: jest.fn().mockReturnValue(of(true)),
    }),
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [ConfirmationService, { provide: MatDialog, useValue: matDialogMock }],
    });
    service = TestBed.inject(ConfirmationService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should open the dialog', () => {
    const data = {
      title: 'Test Title',
      message: 'Test Message',
      cancelText: 'Cancel',
      confirmText: 'Confirm',
    };
    service.confirm({
      ...data,
    });

    expect(matDialogMock.open).toHaveBeenCalledWith(ConfirmDialogComponent, {
      data,
    });
  });

  it('should call afterClosed and callback with the correct value', (done) => {
    const callbackMock = jest.fn();

    service.confirm({
      message: 'Test Message',
      callback: callbackMock,
    });

    expect(matDialogMock.open).toHaveBeenCalled();
    expect(matDialogMock.open().afterClosed).toHaveBeenCalled();

    matDialogMock
      .open()
      .afterClosed()
      .subscribe(() => {
        expect(callbackMock).toHaveBeenCalledWith(true);
        done();
      });
  });
});
