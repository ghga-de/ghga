/**
 * Public key input component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import {
  ChangeDetectionStrategy,
  Component,
  effect,
  input,
  model,
} from '@angular/core';
import { FormControl, FormsModule, ReactiveFormsModule } from '@angular/forms';
import {
  FormValueControl,
  schema,
  validate,
  ValidationError,
} from '@angular/forms/signals';
import { ErrorStateMatcher } from '@angular/material/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';

/**
 * Trim Crypt4GH public key headers/footers and fix Base64 padding
 * @param key Raw key string to trim
 * @returns Trimmed and padded key
 */
function trimKey(key: string): string {
  // Remove Crypt4GH headers, whitespace, and surrounding dashes
  key = key
    .replace(/-----(BEGIN|END) CRYPT4GH PUBLIC KEY-----/g, '')
    .replace(/\s/g, '')
    .replace(/^-+/, '')
    .replace(/[-=]+$/, '');

  // Fix Base64 padding
  const paddingNeeded = key.length % 4;
  if (paddingNeeded) {
    key += '='.repeat(4 - paddingNeeded);
  }
  return key;
}

/**
 * Check if two Uint8Array objects are equal
 * @param arr1 First array
 * @param arr2 Second array
 * @returns True if arrays are equal
 */
function arraysEqual(arr1: Uint8Array, arr2: Uint8Array): boolean {
  return arr1.length === arr2.length && arr1.every((val, i) => val === arr2[i]);
}

/**
 * Validate Crypt4GH public key
 * @param key Key string to validate
 * @returns 0 if valid, otherwise an error code: 1=empty, 2=private key, 3=invalid format
 */
function validatePubKey(key: string): number {
  // Check for private key patterns
  if (key.match(/-.*PRIVATE.*-/)) {
    return 2;
  }

  // Trim and check if empty
  key = trimKey(key);
  if (!key) {
    return 1;
  }

  // Decode Base64
  let binKey: Uint8Array;
  try {
    const binStr = atob(key);
    binKey = Uint8Array.from(binStr, (char) => char.charCodeAt(0));
  } catch {
    return 3;
  }

  // Validate key length (32 bytes for Crypt4GH public key)
  if (binKey.length !== 32) {
    // Check if it's a private key (starts with 'c4gh-' prefix)
    const privateKeyPrefix = new TextEncoder().encode('c4gh-');
    if (arraysEqual(binKey.subarray(0, 5), privateKeyPrefix)) {
      return 2;
    }
    return 3;
  }

  return 0;
}

/**
 * Reusable form control component for entering a Crypt4GH public key
 */
@Component({
  selector: 'app-pubkey-input',
  imports: [MatFormFieldModule, MatInputModule, FormsModule, ReactiveFormsModule],
  templateUrl: './pubkey-input.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PubkeyFieldComponent implements FormValueControl<string> {
  /**
   * Validation schema for Crypt4GH public keys
   * Apply to form fields using: apply(fieldPath, PubkeyFieldComponent.schema)
   */
  static schema = schema<string>((fieldPath) => {
    validate(fieldPath, ({ value }) => {
      const errorCode = validatePubKey(value() as string);

      if (errorCode !== 0) {
        const messages: Record<number, string> = {
          1: 'The key is empty.',
          2: 'Please do not paste your private key here!',
          3: 'This does not seem to be a Base64 encoded Crypt4GH key.',
        };
        return { kind: 'invalidKey', message: messages[errorCode] ?? '' };
      }
      return null;
    });
  });
  /** Input field label */
  label = input('Your public Crypt4GH key');

  /** Hint text displayed below input */
  hint = input(
    'Please enter your public Crypt4GH key (in Base64 encoded format) above, so that we can encrypt your data.',
  );

  /** Current value (required by FormValueControl) */
  value = model.required<string>();

  /** Validation errors from parent form */
  errors = input<readonly ValidationError.WithOptionalField[]>([]);

  /** Invalid state from parent form */
  invalid = input(false);

  /** Internal FormControl for Material form field integration */
  #formControl = new FormControl('');

  /** Shows errors when field has value and is invalid */
  errorStateMatcher: ErrorStateMatcher = {
    isErrorState: () => !!this.value() && this.invalid(),
  };

  /**
   * Expose formControl for template
   * @returns Internal FormControl instance
   */
  get formControl() {
    return this.#formControl;
  }

  /**
   * Trimmed key value ready for submission
   * @returns Processed key without headers/footers and with correct padding
   */
  get trimmedKey(): string {
    return trimKey(this.value());
  }

  #validateEffect = effect(() => {
    if (this.invalid()) {
      this.#formControl.setErrors({ invalid: true });
    } else {
      this.#formControl.setErrors(null);
    }
  });

  #valueEffect = effect(() => {
    this.#formControl.setValue(this.value(), { emitEvent: false });
  });
}
