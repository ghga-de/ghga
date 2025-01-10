/**
 * Test the confirm TOTP component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { AuthService } from '@app/auth/services/auth.service';
import { ConfirmTotpComponent } from './confirm-totp.component';

/**
 * Mock the auth service as needed for the confirm TOTP component
 */
class MockAuthService {}

describe('ConfirmTotpComponent', () => {
  let component: ConfirmTotpComponent;
  let fixture: ComponentFixture<ConfirmTotpComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConfirmTotpComponent, NoopAnimationsModule],
      providers: [{ provide: AuthService, useClass: MockAuthService }],
    }).compileComponents();

    fixture = TestBed.createComponent(ConfirmTotpComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
