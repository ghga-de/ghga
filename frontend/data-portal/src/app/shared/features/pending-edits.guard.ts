/**
 * A guard to prevent navigation away from components with unsaved changes.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { inject } from '@angular/core';
import { CanDeactivateFn } from '@angular/router';
import { ConfirmationService } from '../services/confirmation.service';

/**
 * Interface for components that have pending edits functionality
 */
export interface HasPendingEdits {
  /**
   * Check if the component has unsaved changes
   * @returns true if there are pending edits, false otherwise
   */
  hasPendingEdits(): boolean;
}

/**
 * Generic guard to prevent navigation away from components with unsaved changes.
 * Components must implement the HasPendingEdits interface.
 * @param component the component to check for pending edits
 * @returns a guard result which is or can be resolved to a boolean
 */
export const pendingEditsGuard: CanDeactivateFn<HasPendingEdits> = (component) => {
  const confirmationService = inject(ConfirmationService);

  if (component.hasPendingEdits()) {
    return new Promise<boolean>((resolve) => {
      confirmationService.confirm({
        title: 'Unsaved changes',
        message: 'You have unsaved changes. Do you want to leave without saving?',
        cancelText: 'Stay on this page',
        confirmText: 'Discard changes',
        confirmClass: 'danger',
        callback: (confirmed) => {
          resolve(!!confirmed);
        },
      });
    });
  }

  return true;
};
