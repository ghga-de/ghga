/**
 * Public key input component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  model,
  output,
  signal,
} from '@angular/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';

/**
 * Reusable component for entering a Crypt4GH public key
 */
@Component({
  selector: 'app-pubkey-input',
  imports: [MatFormFieldModule, MatInputModule],
  templateUrl: './pubkey-input.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PubkeyInputComponent {
  /** Label for the input field */
  label = input<string>('Your public Crypt4GH key');

  /** Hint text to display below the input */
  hint = input<string>(
    'Please enter your public Crypt4GH key (in Base64 encoded format) above, so that we can encrypt your data.',
  );

  /** The public key value */
  value = model<string>('');

  /** Error message for invalid keys */
  error = signal<string>('');

  /** Whether the key is valid */
  isValid = computed(() => !this.error() && this.value().length > 0);

  /** Event emitted when the key changes */
  valueChange = output<string>();

  /** Event emitted when the key validity changes */
  validityChange = output<boolean>();

  /**
   * Remove headers and fix padding of the given base64 encoded key
   * @param key - the key to be trimmed
   * @returns the trimmed key
   */
  #trimKey(key: string): string {
    // allow and trim headers and footers for public keys
    key = key
      .replace(/-----(BEGIN|END) CRYPT4GH PUBLIC KEY-----/g, '')
      .replace(/\s/g, '')
      .replace(/^-+/, '')
      .replace(/[-=]+$/, '');
    const fix = key.length % 4;
    if (fix) {
      key += '='.repeat(4 - fix);
    }
    return key;
  }

  /**
   * Check whether the given key is a valid public key.
   * @param key - the key in question
   * @returns an internal error code
   */
  #checkPubKey(key: string): number {
    if (key.match(/-.*PRIVATE.*-/)) {
      return 2; // if any kind of private key has been posted
    }
    // allow and trim headers and footers for public keys
    key = this.#trimKey(key);
    if (!key) {
      return 1; // key is empty after trimming
    }
    // Base64 decode the key
    let binKey: Uint8Array;
    try {
      const binStr = atob(key);
      binKey = new Uint8Array(binStr.length);
      for (let i = 0; i < binStr.length; i++) {
        binKey[i] = binStr.charCodeAt(i);
      }
    } catch {
      return 3; // key is not a valid Base64 string
    }
    if (binKey.length !== 32) {
      // key does not have the right length for a Crypt4GH public key
      const prefix = new TextEncoder().encode('c4gh-');
      if (this.#compareUint8Arrays(binKey.subarray(0, 5), prefix)) {
        return 2; // key is actually a Base64 encoded Crypt4GH private key
      }
      return 3; // key is something else
    }
    return 0; // key seems to be ok
  }

  /**
   * Compare two Uint8Array objects for equality
   * @param arr1 - the first array
   * @param arr2 - the second array
   * @returns true if the arrays are equal, false otherwise
   */
  #compareUint8Arrays(arr1: Uint8Array, arr2: Uint8Array): boolean {
    return (
      arr1.length === arr2.length && arr1.every((value, index) => value === arr2[index])
    );
  }

  /**
   * Handle input events and update the model
   * @param event - the input event
   */
  onInput(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.value.set(input.value);
    this.checkPubKey();
  }

  /**
   * Check whether the entered public key is valid
   * and set error accordingly.
   */
  checkPubKey(): void {
    const errorCode = this.#checkPubKey(this.value());
    const errorMessage =
      {
        1: 'The key is empty.',
        2: 'Please do not paste your private key here!',
        3: 'This does not seem to be a Base64 encoded Crypt4GH key.',
      }[errorCode] ?? '';
    this.error.set(errorMessage);
    this.validityChange.emit(this.isValid());
  }

  /**
   * Get the trimmed public key value
   * @returns the trimmed key or empty string if invalid
   */
  getTrimmedKey(): string {
    return this.error() ? '' : this.#trimKey(this.value());
  }
}
