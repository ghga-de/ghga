/**
 * Unit tests for public key input component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { apply, form } from '@angular/forms/signals';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { PubkeyFieldComponent } from './pubkey-input';

describe('PubkeyFieldComponent', () => {
  let component: PubkeyFieldComponent;
  let fixture: ComponentFixture<PubkeyFieldComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PubkeyFieldComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(PubkeyFieldComponent);
    component = fixture.componentInstance;

    // Initialize the value signal as required by FormValueControl
    component.value.set('');

    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should provide trimmedKey getter', () => {
    component.value.set('MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI');
    expect(component.trimmedKey).toBe('MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI=');
  });

  it('should trim headers and footers', () => {
    const keyWithHeaders = `-----BEGIN CRYPT4GH PUBLIC KEY-----
MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI
-----END CRYPT4GH PUBLIC KEY-----`;
    component.value.set(keyWithHeaders);
    expect(component.trimmedKey).toBe('MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI=');
  });

  it('should fix base64 padding', () => {
    const keyWithoutPadding = 'MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMT';
    component.value.set(keyWithoutPadding);
    const trimmed = component.trimmedKey;
    expect(trimmed.endsWith('=')).toBe(true);
  });

  describe('validation schema', () => {
    it('should detect empty key', () => {
      TestBed.runInInjectionContext(() => {
        const model = signal({ pubkey: '' });
        const testForm = form(model, (p) => {
          apply(p.pubkey, PubkeyFieldComponent.schema);
        });

        expect(testForm().valid()).toBe(false);
        expect(testForm.pubkey().errors().length).toBeGreaterThan(0);
        expect(testForm.pubkey().errors()[0].message).toBe('The key is empty.');
      });
    });

    it('should detect empty key after trimming', () => {
      TestBed.runInInjectionContext(() => {
        const model = signal({ pubkey: '   ' });
        const testForm = form(model, (p) => {
          apply(p.pubkey, PubkeyFieldComponent.schema);
        });

        expect(testForm().valid()).toBe(false);
        expect(testForm.pubkey().errors()[0].message).toBe('The key is empty.');
      });
    });

    it('should detect private key by header', () => {
      TestBed.runInInjectionContext(() => {
        const model = signal({ pubkey: '-----BEGIN CRYPT4GH PRIVATE KEY-----' });
        const testForm = form(model, (p) => {
          apply(p.pubkey, PubkeyFieldComponent.schema);
        });

        expect(testForm().valid()).toBe(false);
        expect(testForm.pubkey().errors()[0].message).toBe(
          'Please do not paste your private key here!',
        );
      });
    });

    it('should detect invalid base64', () => {
      TestBed.runInInjectionContext(() => {
        const model = signal({ pubkey: 'not-valid-base64!!!' });
        const testForm = form(model, (p) => {
          apply(p.pubkey, PubkeyFieldComponent.schema);
        });

        expect(testForm().valid()).toBe(false);
        expect(testForm.pubkey().errors()[0].message).toBe(
          'This does not seem to be a Base64 encoded Crypt4GH key.',
        );
      });
    });

    it('should accept valid 32-byte key', () => {
      TestBed.runInInjectionContext(() => {
        const model = signal({ pubkey: 'MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI' });
        const testForm = form(model, (p) => {
          apply(p.pubkey, PubkeyFieldComponent.schema);
        });

        expect(testForm().valid()).toBe(true);
      });
    });

    it('should reject key that is too short (16 bytes)', () => {
      TestBed.runInInjectionContext(() => {
        const model = signal({ pubkey: 'MTIzNDU2Nzg5MDEyMzQ1Ng==' });
        const testForm = form(model, (p) => {
          apply(p.pubkey, PubkeyFieldComponent.schema);
        });

        expect(testForm().valid()).toBe(false);
        expect(testForm.pubkey().errors()[0].message).toBe(
          'This does not seem to be a Base64 encoded Crypt4GH key.',
        );
      });
    });

    it('should reject key that is too long (64 bytes)', () => {
      TestBed.runInInjectionContext(() => {
        const model = signal({
          pubkey:
            'MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDEyMzQ1Ng==',
        });
        const testForm = form(model, (p) => {
          apply(p.pubkey, PubkeyFieldComponent.schema);
        });

        expect(testForm().valid()).toBe(false);
        expect(testForm.pubkey().errors()[0].message).toBe(
          'This does not seem to be a Base64 encoded Crypt4GH key.',
        );
      });
    });

    it('should accept key with headers and footers', () => {
      TestBed.runInInjectionContext(() => {
        const model = signal({
          pubkey: `-----BEGIN CRYPT4GH PUBLIC KEY-----
MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI
-----END CRYPT4GH PUBLIC KEY-----`,
        });
        const testForm = form(model, (p) => {
          apply(p.pubkey, PubkeyFieldComponent.schema);
        });

        expect(testForm().valid()).toBe(true);
      });
    });

    it('should detect encoded private key', () => {
      TestBed.runInInjectionContext(() => {
        const privateKeyEncoded = btoa('c4gh-test-private-key-content-here');
        const model = signal({ pubkey: privateKeyEncoded });
        const testForm = form(model, (p) => {
          apply(p.pubkey, PubkeyFieldComponent.schema);
        });

        expect(testForm().valid()).toBe(false);
        expect(testForm.pubkey().errors()[0].message).toBe(
          'Please do not paste your private key here!',
        );
      });
    });
  });
});
