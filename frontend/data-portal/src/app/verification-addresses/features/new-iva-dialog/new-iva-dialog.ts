/**
 * Dialog to enter the details of a new IVA
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, ElementRef, inject, viewChild } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';

import { A11yModule } from '@angular/cdk/a11y';
import {
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import {
  MatDialogActions,
  MatDialogContent,
  MatDialogModule,
  MatDialogRef,
  MatDialogTitle,
} from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { IvaType } from '@app/verification-addresses/models/iva';
import { IvaTypePipe } from '@app/verification-addresses/pipes/iva-type-pipe';
import { NgxMatInputTelComponent } from 'ngx-mat-input-tel';
import { map, startWith } from 'rxjs';

/**
 * IVA creation dialog component
 *
 * This component uses the international telephone input for Angular Material
 * provided by [ngxMatInputTel](https://github.com/rbalet/ngx-mat-input-tel).
 * The full validation of the phone numbers is done on the server side.
 * Might be refactored to use a signal form once ngxMatInputTel supports it.
 */
@Component({
  selector: 'app-new-iva-dialog',
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatDialogModule,
    MatDialogTitle,
    MatDialogContent,
    MatDialogActions,
    MatButtonToggleModule,
    NgxMatInputTelComponent,
    A11yModule,
  ],
  providers: [IvaTypePipe],
  templateUrl: './new-iva-dialog.html',
})
export class NewIvaDialogComponent {
  #dialogRef = inject(
    MatDialogRef<NewIvaDialogComponent, { type: IvaType; value: string }>,
  );
  #ivaTypePipe = inject(IvaTypePipe);

  form = new FormGroup({
    type: new FormControl<keyof typeof IvaType | null>(null, Validators.required),
    value: new FormControl<string>('', Validators.required),
  });

  /**
   * Signal indicating whether the form is invalid
   * @returns true if the form is invalid, false otherwise
   */
  isInvalid = toSignal(
    this.form.statusChanges.pipe(
      startWith('INVALID'),
      map((status) => status !== 'VALID'),
    ),
  );

  /**
   * Value prompts for the different IVA types
   */
  valuePrompts: { [key in keyof typeof IvaType]: string } = {
    Phone: 'Please enter your phone number to receive an SMS:',
    InPerson: 'Please enter a meeting location:',
    // the following options should not be selectable any more:
    Fax: '',
    PostalAddress: '',
  };

  /**
   * Get the display name for an IVA type
   * @param type the IVA type in question
   * @returns the display name
   */
  #ivaTypeName(type: IvaType): string {
    return this.#ivaTypePipe.transform(type).name;
  }

  /**
   * All possible IVA types
   */
  types = Object.entries(IvaType)
    .filter((entry) => this.valuePrompts[entry[0] as keyof typeof IvaType])
    .map((entry) => ({
      value: entry[0] as keyof typeof IvaType,
      text: this.#ivaTypeName(entry[1]),
    }));

  valueField = viewChild('valueField', { read: ElementRef });

  /**
   * Selected IVA type
   * @returns the selected IVA type
   */
  get type(): keyof typeof IvaType | null {
    return this.form.controls.type.value;
  }

  /**
   * Entered IVA value
   * @returns the entered IVA value
   */
  get value(): string | null {
    return this.form.controls.value.value;
  }

  /**
   * Get the value prompt for the selected IVA type
   * @returns the text to be shown as prompt for the value input
   */
  get valuePrompt(): string {
    return this.type ? this.valuePrompts[this.type] : '';
  }

  /**
   * Focus the value field when the type was changed
   */
  onTypeChange(): void {
    this.form.controls.value.reset();
    setTimeout(
      () =>
        this.valueField()
          ?.nativeElement?.closest('mat-form-field')
          ?.querySelector('input')
          ?.focus(),
      5,
    );
  }

  /**
   * Cancel the dialog
   */
  onCancel(): void {
    this.#dialogRef.close(undefined);
  }

  /**
   * Complete the verification and pass the entered IVA data
   */
  onSubmit(): void {
    if (this.form.valid && this.type && this.value) {
      this.#dialogRef.close({
        type: IvaType[this.type],
        value: this.value,
      });
    }
  }
}
