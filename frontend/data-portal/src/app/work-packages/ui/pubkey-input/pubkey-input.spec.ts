/**
 * Unit tests for public key input component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { PubkeyInputComponent } from './pubkey-input';

describe('PubkeyInputComponent', () => {
  let component: PubkeyInputComponent;
  let fixture: ComponentFixture<PubkeyInputComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PubkeyInputComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(PubkeyInputComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize with empty value and no error', () => {
    expect(component.value()).toBe('');
    expect(component.error()).toBe('');
    expect(component.isValid()).toBe(false);
  });

  it('should detect empty key after trimming', () => {
    component.value.set('   ');
    component.checkPubKey();
    expect(component.error()).toBe('The key is empty.');
    expect(component.isValid()).toBe(false);
  });

  it('should detect private key', () => {
    component.value.set('-----BEGIN CRYPT4GH PRIVATE KEY-----');
    component.checkPubKey();
    expect(component.error()).toBe('Please do not paste your private key here!');
    expect(component.isValid()).toBe(false);
  });

  it('should detect invalid base64', () => {
    component.value.set('not-valid-base64!!!');
    component.checkPubKey();
    expect(component.error()).toBe(
      'This does not seem to be a Base64 encoded Crypt4GH key.',
    );
    expect(component.isValid()).toBe(false);
  });

  it('should accept valid 32-byte key', () => {
    component.value.set('MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI');
    component.checkPubKey();
    expect(component.error()).toBe('');
    expect(component.isValid()).toBe(true);
  });

  it('should reject key that is too short (16 bytes)', () => {
    component.value.set('MTIzNDU2Nzg5MDEyMzQ1Ng==');
    component.checkPubKey();
    expect(component.error()).toBe(
      'This does not seem to be a Base64 encoded Crypt4GH key.',
    );
    expect(component.isValid()).toBe(false);
  });

  it('should reject key that is too long (64 bytes)', () => {
    component.value.set(
      'MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDEyMzQ1Ng==',
    );
    component.checkPubKey();
    expect(component.error()).toBe(
      'This does not seem to be a Base64 encoded Crypt4GH key.',
    );
    expect(component.isValid()).toBe(false);
  });

  it('should trim headers and footers', () => {
    component.value.set(
      `-----BEGIN CRYPT4GH PUBLIC KEY-----
MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI
-----END CRYPT4GH PUBLIC KEY-----`,
    );
    component.checkPubKey();
    expect(component.error()).toBe('');
    // The trimmed key has padding added to make length divisible by 4
    expect(component.getTrimmedKey()).toBe(
      'MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI=',
    );
  });

  it('should fix base64 padding', () => {
    const keyWithoutPadding = 'MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMT';
    component.value.set(keyWithoutPadding);
    const trimmed = component.getTrimmedKey();
    // Should add one '=' for padding
    expect(trimmed.endsWith('=')).toBe(true);
  });

  it('should detect encoded private key', () => {
    // Create a key that starts with 'c4gh-' prefix when decoded
    const privateKeyEncoded = btoa('c4gh-test-private-key-content-here');
    component.value.set(privateKeyEncoded);
    component.checkPubKey();
    expect(component.error()).toBe('Please do not paste your private key here!');
  });

  it('should return empty string for invalid key when getting trimmed key', () => {
    component.value.set('invalid');
    component.checkPubKey();
    expect(component.getTrimmedKey()).toBe('');
  });

  it('should emit validity change event', () => {
    const validitySpy = vitest.fn();
    component.validityChange.subscribe(validitySpy);

    component.value.set('MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI');
    component.checkPubKey();

    expect(validitySpy).toHaveBeenCalledWith(true);
  });
});
