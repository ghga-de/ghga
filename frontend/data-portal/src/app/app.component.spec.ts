/**
 * Test the main app component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { AppComponent } from './app.component';

import { SiteFooterComponent } from './portal/features/site-footer/site-footer.component';
import { SiteHeaderComponent } from './portal/features/site-header/site-header.component';
import { ConfigService } from './shared/services/config.service';

/**
 * Mock the config service as needed for the main app component
 */
class MockConfigService {
  ribbonText = 'Test ribbon';
}

describe('AppComponent', () => {
  let component: AppComponent;
  let fixture: ComponentFixture<AppComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [{ provide: ConfigService, useClass: MockConfigService }],
    })
      .overrideComponent(AppComponent, {
        remove: { imports: [SiteHeaderComponent, SiteFooterComponent] },
      })
      .compileComponents();

    fixture = TestBed.createComponent(AppComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create the app component', () => {
    expect(component).toBeTruthy();
  });

  it('should have a header element', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('header')).not.toBeNull();
  });

  it('should have a main element', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('main')).not.toBeNull();
  });

  it('should have a footer element', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('footer')).not.toBeNull();
  });

  it('should have a version ribbon', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const ribbon = compiled.querySelector('.version-ribbon');
    expect(ribbon).not.toBeNull();
    expect(ribbon!.textContent).toContain('Test ribbon');
  });
});
