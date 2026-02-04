/**
 * Test the user IVA list component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { IvaService } from '@app/ivas/services/iva';
import { UserIvaListComponent } from './user-iva-list';

/**
 * Mock the IVA service as needed by the user IVA list component
 */
class MockIvaService {
  loadUserIvas = () => undefined;
  userIvas = { value: () => [], isLoading: () => false, error: () => undefined };
}

describe('UserIvaListComponent', () => {
  let component: UserIvaListComponent;
  let fixture: ComponentFixture<UserIvaListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UserIvaListComponent],
      providers: [{ provide: IvaService, useClass: MockIvaService }],
    }).compileComponents();

    fixture = TestBed.createComponent(UserIvaListComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should say that there are no user IVAs', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain(
      'You have not yet created any contact addresses.',
    );
  });
});
