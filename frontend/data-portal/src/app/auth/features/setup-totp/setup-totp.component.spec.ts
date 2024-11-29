import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SetupTotpComponent } from './setup-totp.component';

describe('SetupTotpComponent', () => {
  let component: SetupTotpComponent;
  let fixture: ComponentFixture<SetupTotpComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SetupTotpComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(SetupTotpComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
