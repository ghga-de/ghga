/**
 * Test the notification service
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { TestBed } from '@angular/core/testing';
import { MatSnackBar } from '@angular/material/snack-bar';

import { CustomSnackBarComponent } from '../ui/custom-snack-bar/custom-snack-bar';
import { NotificationService } from './notification';

describe('NotificationService', () => {
  const horizontalPosition = 'end';
  const verticalPosition = 'bottom';
  let service: NotificationService;
  let matSnackBar: MatSnackBar;

  beforeEach(() => {
    const mockMatSnackBar = { openFromComponent: jest.fn() };
    TestBed.configureTestingModule({
      providers: [
        NotificationService,
        { provide: MatSnackBar, useValue: mockMatSnackBar },
      ],
    });
    service = TestBed.inject(NotificationService);
    matSnackBar = TestBed.inject(MatSnackBar);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should call openFromComponent properly when showSuccess is called', () => {
    service.showSuccess('Test success message');
    expect(matSnackBar.openFromComponent).toHaveBeenCalledWith(
      CustomSnackBarComponent,
      {
        data: { message: 'Test success message', type: 'success' },
        duration: 3000,
        panelClass: 'snackbar-success',
        horizontalPosition,
        verticalPosition,
      },
    );
  });

  it('should call openFromComponent properly when showInfo is called', () => {
    service.showInfo('Test info message');
    expect(matSnackBar.openFromComponent).toHaveBeenCalledWith(
      CustomSnackBarComponent,
      {
        data: { message: 'Test info message', type: 'info' },
        duration: 3000,
        panelClass: 'snackbar-info',
        horizontalPosition,
        verticalPosition,
      },
    );
  });

  it('should call openFromComponent properly when showWarning is called', () => {
    service.showWarning('Test warning message');
    expect(matSnackBar.openFromComponent).toHaveBeenCalledWith(
      CustomSnackBarComponent,
      {
        data: { message: 'Test warning message', type: 'warning' },
        duration: 4000,
        panelClass: 'snackbar-warning',
        horizontalPosition,
        verticalPosition,
      },
    );
  });

  it('should call openFromComponent properly when showDanger is called', () => {
    service.showDanger('Test danger message');
    expect(matSnackBar.openFromComponent).toHaveBeenCalledWith(
      CustomSnackBarComponent,
      {
        data: { message: 'Test danger message', type: 'danger' },
        duration: 4000,
        panelClass: 'snackbar-danger',
        horizontalPosition,
        verticalPosition,
      },
    );
  });

  it('should call openFromComponent properly when showError is called', () => {
    service.showError('Test error message');
    expect(matSnackBar.openFromComponent).toHaveBeenCalledWith(
      CustomSnackBarComponent,
      {
        data: { message: 'Test error message', type: 'error' },
        duration: 5000,
        panelClass: 'snackbar-error',
        horizontalPosition,
        verticalPosition,
      },
    );
  });
});
