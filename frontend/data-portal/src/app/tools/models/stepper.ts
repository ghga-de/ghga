/**
 * Types for the stepper component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

export type StepStatus = 'idle' | 'ongoing' | 'succeeded' | 'failed';

export type StepDetails = {
  name: string;
  status: StepStatus;
};
