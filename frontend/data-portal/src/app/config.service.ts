import { Injectable } from '@angular/core';

interface Config {
  mass_url: string;
  metldata_url: string;
}

declare global {
  interface Window {
    config: Config;
  }
}

/**
 * The config service provides access to the configuration of the application.
 */
@Injectable({
  providedIn: 'root',
})
export class ConfigService {
  #config: Config;

  /**
   * This constructor initializes the config via the window object
   */
  constructor() {
    this.#config = window.config;
  }

  /**
   * Gets the mass url from the config object.
   * @returns the mass url as a string
   */
  get massUrl(): string {
    return this.#config.mass_url;
  }

  /**
   * Gets the metldataUrl from the config object.
   * @returns the metldataUrl as a string
   */
  get metldataUrl(): string {
    return this.#config.metldata_url;
  }
}
