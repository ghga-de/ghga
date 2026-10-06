/**
 * Unit tests for public key input component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ApplicationRef, Component, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { apply, form, FormField } from '@angular/forms/signals';
import { screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';
import { PubkeyField } from './pubkey-input';

describe('PubkeyField', () => {
  let component: PubkeyField;
  let fixture: ComponentFixture<PubkeyField>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PubkeyField],
    }).compileComponents();

    fixture = TestBed.createComponent(PubkeyField);
    component = fixture.componentInstance;

    // Initialize the value signal as required by FormValueControl
    component.value.set('');

    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should provide trimmedKey getter', () => {
    component.value.set('MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI');
    expect(component.trimmedKey).toBe('MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI=');
  });

  it('should default hint text to encrypt context', () => {
    expect(component.hintText()).toContain('so that we can encrypt your data.');
  });

  it('should allow decrypt context in hint text', async () => {
    fixture.componentRef.setInput('hintAction', 'decrypt');
    await fixture.whenStable();

    expect(component.hintText()).toContain('so that we can decrypt your data.');
  });

  it('should prefer custom hint over generated hint text', async () => {
    fixture.componentRef.setInput('hint', 'Custom key hint');
    fixture.componentRef.setInput('hintAction', 'decrypt');
    await fixture.whenStable();

    expect(component.hintText()).toBe('Custom key hint');
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
          apply(p.pubkey, PubkeyField.schema);
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
          apply(p.pubkey, PubkeyField.schema);
        });

        expect(testForm().valid()).toBe(false);
        expect(testForm.pubkey().errors()[0].message).toBe('The key is empty.');
      });
    });

    it('should detect private key by header', () => {
      TestBed.runInInjectionContext(() => {
        const model = signal({ pubkey: '-----BEGIN CRYPT4GH PRIVATE KEY-----' });
        const testForm = form(model, (p) => {
          apply(p.pubkey, PubkeyField.schema);
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
          apply(p.pubkey, PubkeyField.schema);
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
          apply(p.pubkey, PubkeyField.schema);
        });

        expect(testForm().valid()).toBe(true);
      });
    });

    it('should reject key that is too short (16 bytes)', () => {
      TestBed.runInInjectionContext(() => {
        const model = signal({ pubkey: 'MTIzNDU2Nzg5MDEyMzQ1Ng==' });
        const testForm = form(model, (p) => {
          apply(p.pubkey, PubkeyField.schema);
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
          apply(p.pubkey, PubkeyField.schema);
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
          apply(p.pubkey, PubkeyField.schema);
        });

        expect(testForm().valid()).toBe(true);
      });
    });

    it('should detect encoded private key', () => {
      TestBed.runInInjectionContext(() => {
        const privateKeyEncoded = btoa('c4gh-test-private-key-content-here');
        const model = signal({ pubkey: privateKeyEncoded });
        const testForm = form(model, (p) => {
          apply(p.pubkey, PubkeyField.schema);
        });

        expect(testForm().valid()).toBe(false);
        expect(testForm.pubkey().errors()[0].message).toBe(
          'Please do not paste your private key here!',
        );
      });
    });
  });

  describe('as a form field', () => {
    const VALID_KEY = btoa(String.fromCharCode(...new Uint8Array(32).fill(7)));

    /**
     * A host that binds the input to a form with the key schema
     */
    @Component({
      imports: [PubkeyField, FormField],
      template: '<app-pubkey-input [formField]="keyForm" />',
    })
    class HostComponent {
      model = signal('');
      keyForm = form(this.model, (path) => apply(path, PubkeyField.schema));
    }

    let host: HostComponent;

    beforeEach(async () => {
      const hostFixture = TestBed.createComponent(HostComponent);
      host = hostFixture.componentInstance;
      await hostFixture.whenStable();
    });

    it('should pass the typed key to the form', async () => {
      await userEvent.type(screen.getByRole('textbox'), VALID_KEY);
      expect(host.model()).toBe(VALID_KEY);
      expect(host.keyForm().valid()).toBe(true);
      expect(screen.queryByText(/Base64 encoded Crypt4GH key\./)).toBeNull();
    });

    it('should show the validation message for an invalid key', async () => {
      await userEvent.type(screen.getByRole('textbox'), 'not a key');
      expect(host.model()).toBe('not a key');
      expect(
        await screen.findByText(
          'This does not seem to be a Base64 encoded Crypt4GH key.',
        ),
      ).toBeVisible();
    });

    it('should show the value the form sets', async () => {
      host.model.set(VALID_KEY);
      await TestBed.inject(ApplicationRef).whenStable();
      expect(screen.getByRole('textbox')).toHaveValue(VALID_KEY);
    });
  });
});
