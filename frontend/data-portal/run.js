#!/usr/bin/env node

/**
 * Run the development or production server for the data portal.
 *
 * Syntax: run.js [--dev [--with-backend] [--with-oidc]]
 */

import { execFileSync, spawnSync } from 'child_process';
import { Resolver } from 'dns/promises';
import fs from 'fs';
import * as yaml from 'js-yaml';
import path from 'path';
import { fileURLToPath } from 'url';

const NAME = 'data-portal';
const DEFAULT_BACKEND = 'https://data.staging.ghga.dev';

// In production the settings that must not be baked into the image arrive on a mounted
// secrets volume; in development they come from a gitignored file next to this script.
const DOTENV_PATH = '/secrets/.env';
const LOCAL_ENV_PATH = 'local.env';

const args = process.argv.slice(1);
const DEV = args.includes('--dev');
const WITH_BACKEND = args.includes('--with-backend');
const WITH_OIDC = args.includes('--with-oidc');
const MODE = { dev: DEV, withBackend: WITH_BACKEND, withOidc: WITH_OIDC };

// Settings the server needs and the browser must not see
const SERVER_KEYS = [
  'host',
  'port',
  'ssl',
  'ssl_cert',
  'ssl_key',
  'log_level',
  'basic_auth',
  'root_files',
];

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// The platform version of a checkout without git or a ghga/ tag
const FALLBACK_VERSION = '0.0.0+dev';

/**
 * Turn `git describe` output into a semver platform version.
 *
 * A copy of scripts/platform_version.py, which this script cannot import;
 * docs/releases.md defines the format.
 *
 * @param {string} described - e.g. ghga/15.3.1-rc.8-71-g44594f5-dirty
 * @returns {string} The version, e.g. 15.3.1-rc.8+dev.71.44594f5.dirty.
 */
export function fromDescribe(described) {
  const match = described.match(
    /^ghga\/(?<tag>.+?)(?:-(?<count>\d+)-g(?<sha>[0-9a-f]+))?(?<dirty>-dirty)?$/,
  );
  if (!match) return FALLBACK_VERSION;
  const { tag, count, sha, dirty } = match.groups;
  const build = count ? ['dev', count, sha] : [];
  if (dirty) build.push('dirty');
  return build.length ? `${tag}+${build.join('.')}` : tag;
}

/**
 * Derive the platform version from the checkout this script runs in.
 *
 * @returns {string} The version, e.g. 15.3.1-rc.8+dev.71.44594f5.
 */
function checkoutVersion() {
  try {
    return fromDescribe(
      execFileSync(
        'git',
        ['describe', '--tags', '--match', 'ghga/*', '--dirty', '--abbrev=7'],
        { cwd: __dirname, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] },
      ).trim(),
    );
  } catch {
    return FALLBACK_VERSION;
  }
}

/**
 * Inject the version from package.json into the settings.
 *
 * package.json declares the placeholder 0.0.0 (ADR-0046), which the image build
 * replaces with the platform version; outside an image, the checkout gives it.
 */
function setVersion(settings) {
  const packageJsonPath = path.join(__dirname, 'package.json');
  const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
  let version = packageJson.version;
  if (!version) {
    throw new Error(`Version not found in ${packageJsonPath}`);
  }
  if (version === '0.0.0') {
    version = checkoutVersion();
  }
  const ribbonText = settings.ribbon_text;
  if (ribbonText && ribbonText.includes('$v')) {
    settings.ribbon_text = ribbonText.replace('$v', version);
  }
  settings.version = version;
}

/**
 * Parse a .env file and return its key-value pairs.
 *
 * Follows common dotenv conventions: blank lines and # comments are ignored,
 * keys may carry an optional `export ` prefix, and values may be single- or
 * double-quoted (inner whitespace preserved). Double-quoted values expand the
 * \n, \r, \t, \" and \\ escapes; single-quoted ones are literal. Inline
 * comments and variable interpolation are not supported.
 *
 * @param {string} filePath - Path to the .env file.
 * @returns {Object} Parsed key-value pairs.
 */
export function parseEnvFile(filePath) {
  let content;
  try {
    content = fs.readFileSync(filePath, 'utf8');
  } catch (e) {
    if (e.code !== 'ENOENT') throw e;
    return {};
  }
  const result = {};
  for (const line of content.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eq = trimmed.indexOf('=');
    if (eq === -1) continue;
    const key = trimmed
      .slice(0, eq)
      .trim()
      .replace(/^export\s+/, '');
    let value = trimmed.slice(eq + 1).trim();
    const quote = value[0];
    if (
      (quote === '"' || quote === "'") &&
      value.length >= 2 &&
      value.endsWith(quote)
    ) {
      value = value.slice(1, -1);
      if (quote === '"') {
        value = value.replace(/\\([nrt"\\])/g, (_, c) =>
          c === 'n' ? '\n' : c === 'r' ? '\r' : c === 't' ? '\t' : c,
        );
      }
    }
    result[key] = value;
  }
  return result;
}

/**
 * Put the variables of a .env file into the process environment.
 *
 * Variables already set in the environment win, so an inline `data_portal_x=... just fe-dev`
 * still overrides the file. Everything the file defines becomes a real environment variable,
 * not just the settings keys, so consumers outside the settings schema — `proxy.conf.mjs`
 * reads `data_portal_ignore_cert` directly — are served by the same file.
 *
 * @param {string} filePath - Path to the .env file.
 */
function exportEnvFile(filePath) {
  for (const [key, value] of Object.entries(parseEnvFile(filePath))) {
    if (process.env[key] === undefined) {
      process.env[key] = value;
    }
  }
}

/**
 * Reads and merges configuration settings from default and specific YAML files.
 * Overrides settings with environment variables prefixed with the application name.
 * Variables from the .env file at DOTENV_PATH are used as a fallback when a variable
 * is not set in the process environment, but both take precedence over YAML settings.
 *
 * @returns {Object} The merged configuration settings.
 * @throws {Error} If there is an error reading the configuration files.
 */
function readSettings() {
  // Read the default configuration file
  const defaultSettingsPath = path.join(__dirname, `${NAME}.default.yaml`);
  const defaultSettings = yaml.load(fs.readFileSync(defaultSettingsPath, 'utf8'));

  // Read the (optional) development or production specific configuration file
  const specificSettingsPath = DEV ? `${NAME}.dev.yaml` : `${NAME}.yaml`;

  let specificSettings = {};
  try {
    specificSettings = yaml.load(fs.readFileSync(specificSettingsPath, 'utf8'));
  } catch (e) {
    if (e.code !== 'ENOENT') throw e; // ignore non-existing file
  }

  // Merge the default and specific settings, then let the environment override them
  return applyEnv(
    { ...defaultSettings, ...specificSettings },
    process.env,
    parseEnvFile(DOTENV_PATH),
  );
}

/**
 * Override settings with environment variables or .env file variables.
 *
 * A variable is named after the app and the setting, fully lower or fully upper case
 * (`data_portal_port` or `DATA_PORTAL_PORT`, not mixed). The process environment takes
 * precedence over the .env file. A value is converted to the type of the setting it
 * overrides: JSON for an object, `true` (any case) for a boolean, a float for a number.
 *
 * @param {Object} settings - The settings to override, changed in place.
 * @param {Object} env - The process environment.
 * @param {Object} dotenv - The variables of the .env file.
 * @returns {Object} The settings.
 */
export function applyEnv(settings, env, dotenv) {
  const prefix = NAME.replaceAll('-', '_');
  for (const key of Object.keys(settings)) {
    const envVarName = `${prefix}_${key}`;
    const value = settings[key];
    let envVarValue =
      env[envVarName] ??
      env[envVarName.toUpperCase()] ??
      dotenv[envVarName] ??
      dotenv[envVarName.toUpperCase()];
    if (envVarValue === undefined) continue;
    if (typeof value === 'object' && value !== null) {
      envVarValue = JSON.parse(envVarValue);
    } else if (typeof value === 'boolean') {
      envVarValue = envVarValue.toLowerCase() === 'true';
    } else if (typeof value === 'number') {
      envVarValue = parseFloat(envVarValue);
    }
    settings[key] = envVarValue;
  }
  return settings;
}

/**
 * Adapt the settings to the mode the launcher runs in.
 *
 * With a backend or OIDC, a missing or local base URL is replaced by the staging
 * backend; OIDC also needs HTTPS on port 443.
 *
 * @param {Object} settings - The settings, changed in place.
 * @param {{dev: boolean, withBackend: boolean, withOidc: boolean}} mode - The mode.
 * @returns {{message: string, adapted: boolean}} What the launcher runs, for the log,
 *   and whether a setting was changed.
 */
export function adaptSettings(settings, { dev, withBackend, withOidc }) {
  if (!dev) return { message: 'Running in production mode', adapted: false };
  let message = 'Running in development mode';
  let adapted = false;
  if (withBackend || withOidc) {
    const baseUrl = settings.base_url;
    if (
      !baseUrl ||
      baseUrl.startsWith('http://127.') ||
      baseUrl.startsWith('http://localhost')
    ) {
      settings.base_url = DEFAULT_BACKEND;
      adapted = true;
    }
  }
  if (withBackend) {
    const baseUrl = settings.base_url;
    message += ` with ${baseUrl.split('://')[1] || baseUrl} as backend`;
  } else {
    message += ' with mock API';
  }
  if (withOidc) {
    message += ' and authentication via OIDC';
    if (settings.port !== 443 || !settings.ssl) {
      settings.port = 443;
      settings.ssl = true;
      adapted = true;
    }
  } else {
    message += ' and mock authentication';
  }
  return { message, adapted };
}

/**
 * The settings the browser gets as `window.config`.
 *
 * @param {Object} settings - All settings.
 * @param {{dev: boolean, withBackend: boolean, withOidc: boolean}} mode - The mode.
 * @returns {Object} The settings without the server-only ones, plus the mock flags in
 *   development.
 */
export function browserConfig(settings, { dev, withBackend, withOidc }) {
  const config = Object.fromEntries(
    Object.entries(settings).filter(([key]) => !SERVER_KEYS.includes(key)),
  );
  if (dev) {
    config.mock_api = !withBackend;
    config.mock_oidc = !withOidc;
  }
  return config;
}

/**
 * Get the subdirectory with the browser files.
 *
 * @param {string} distDir - The distribution directory.
 */
function getBrowserDir(distDir) {
  const browserDir = path.join(distDir, NAME, 'browser');
  // Support for flattened distribution directory
  return fs.existsSync(browserDir) ? browserDir : distDir;
}

/**
 * Write the browser config into the config file in the appropriate output directory.
 *
 * @param {Object} config - The browser config to write.
 * @throws {Error} If the output directory does not exist.
 */
function writeSettings(config) {
  const outputDir = DEV ? 'public' : getBrowserDir('dist');

  // Ensure the output directory exists
  if (!fs.existsSync(outputDir)) {
    throw new Error(`Output directory not found: ${outputDir}`);
  }

  const configPath = path.join(outputDir, 'config.js');
  const configScript = `window.config = ${JSON.stringify(config)};`;
  fs.writeFileSync(configPath, configScript, 'utf8');
}

/**
 * Creates the given root files (these can be used e.g. for site verification).
 * @param {Object|string} rootFiles - object with file names and contents
 */
function addRootFiles(rootFiles) {
  if (!rootFiles) return;
  if (typeof rootFiles !== 'object') {
    console.error('root_files must be an object with file names and contents.');
    return;
  }
  const rootDir = DEV ? 'public' : getBrowserDir('dist');
  for (const [filename, value] of Object.entries(rootFiles)) {
    const targetPath = path.join(rootDir, filename);
    fs.writeFileSync(targetPath, value || '', 'utf8');
    console.log(`Created root file: ${filename}`);
  }
}

/**
 * Find the IP address for a given hostname
 */
async function getIpAddress(hostname) {
  // Query a public resolver directly rather than the system one, so that the
  // /etc/hosts entry we are about to add cannot shadow the real answer.
  const resolver = new Resolver();
  resolver.setServers(['8.8.8.8']);
  let addresses;
  try {
    addresses = await resolver.resolve4(hostname);
  } catch {
    addresses = [];
  }
  if (!addresses.length) {
    console.error(`Cannot resolve ${hostname}`);
    process.exit(1);
  }
  return addresses[0];
}

/**
 * Add an entry to the /etc/hosts file.
 */
function addHostEntry(name, ip) {
  const hostsFile = '/etc/hosts';
  const hostsContent = fs.readFileSync(hostsFile, 'utf8');
  if (!hostsContent.includes(` ${name}\n`)) {
    spawnSync('sudo', ['sh', '-c', `echo "${ip} ${name}" >> ${hostsFile}`], {
      stdio: 'inherit',
    });
    console.log(`Added ${name} to ${hostsFile}.`);
  } else {
    console.log(`${name} already exists in ${hostsFile}.`);
  }
}

/**
 * Run the development server on the specified host and port.
 */
async function runDevServer(
  host,
  port,
  ssl,
  sslCert,
  sslKey,
  logLevel,
  baseUrl,
  basicAuth,
) {
  console.log('Running the development server...');

  const { hostname } = new URL(baseUrl);
  if (!hostname) {
    console.error(`Invalid URL: ${baseUrl}`);
    return;
  }

  if (WITH_BACKEND) {
    console.log(`Using ${hostname} as backend for API calls via proxy.`);
  } else {
    console.log('Using the mock service worker for API calls.');
  }
  if (WITH_OIDC) {
    console.log('Using OIDC for authentication.');
    if (port != 443 || !ssl) {
      port = 443;
      ssl = true;
      console.log('The server must use HTTPS for OIDC.');
    }
  } else {
    console.log('Using the mock service worker for authentication.');
  }
  if (!WITH_BACKEND && !WITH_OIDC) {
    basicAuth = null;
  }

  if (WITH_OIDC && host != hostname) {
    const ipAddress = await getIpAddress(hostname);
    addHostEntry(hostname, ipAddress);
    console.log(`Your host computer should resolve ${hostname} to ${host}.`);
    console.log(`Please point your browser to: ${baseUrl}`);
  }

  // export settings used in the proxy config
  process.env.data_portal_base_url = baseUrl;
  if (basicAuth) {
    process.env.data_portal_basic_auth = basicAuth;
  } else {
    delete process.env.data_portal_basic_auth;
  }
  if (WITH_BACKEND) {
    process.env.data_portal_with_backend = true;
  } else {
    delete process.env.data_portal_with_backend;
  }
  if (WITH_OIDC) {
    process.env.data_portal_with_oidc = true;
  } else {
    delete process.env.data_portal_with_oidc;
  }

  const params = ['start', '--', '--host', host, '--port', port];
  if (ssl) {
    params.push('--ssl', '--ssl-cert', sslCert, '--ssl-key', sslKey);
  }
  if (logLevel?.toLowerCase() === 'debug') {
    params.push('--verbose');
  }

  const result = spawnSync('npm', params, {
    stdio: 'inherit',
  });

  if (result.error) {
    console.error(result.error.message);
    process.exit(1);
  }

  process.exit(result.status);
}

/**
 * Run the production server on the specified host and port.
 *
 * It is assumed that the application has already been built
 * and that the "serve" package is installed globally.
 */
function runProdServer(host, port, ssl, sslCert, sslKey, logLevel) {
  console.log('Running the production server...');

  const runDir = __dirname;
  const confFile = path.join(runDir, 'sws.toml');
  const distDir = getBrowserDir(path.join(runDir, 'dist'));
  process.chdir(distDir);

  const params = [
    '-a',
    host,
    '-p',
    port,
    '-g',
    logLevel.toLowerCase(),
    '-d',
    '.',
    '--page-fallback',
    './index.html',
    '-w',
    confFile,
  ];
  if (ssl) {
    params.push('--http2', '--http2-tls-cert', sslCert, '--http2-tls-key', sslKey);
  }

  const result = spawnSync('static-web-server', params, {
    stdio: 'inherit',
  });

  if (result.error) {
    console.error(result.error.message);
    process.exit(1);
  }

  process.exit(result.status);
}

/**
 * Main entry point.
 */
async function main() {
  process.chdir(__dirname);

  if (DEV) {
    exportEnvFile(LOCAL_ENV_PATH);
  }

  const settings = readSettings();
  setVersion(settings);
  const { message, adapted } = adaptSettings(settings, MODE);

  const {
    host,
    port,
    ssl,
    ssl_cert,
    ssl_key,
    log_level: logLevel,
    base_url: baseUrl,
    basic_auth: basicAuth,
    root_files: rootFiles,
  } = settings;

  console.log(message);
  console.log(`Runtime settings${adapted ? ' (adapted)' : ''}:`);

  console.table(settings);

  if (!host || !port) {
    console.error('Host and port must be specified');
    process.exit(1);
  }
  if (!baseUrl) {
    console.error('The base URL must be specified');
    process.exit(1);
  }

  writeSettings(browserConfig(settings, MODE));

  addRootFiles(rootFiles);

  await (DEV ? runDevServer : runProdServer)(
    host,
    port,
    ssl,
    ssl_cert,
    ssl_key,
    logLevel,
    baseUrl,
    basicAuth,
  );
}

// Start only when run as a script, so run.test.js can import the functions above
if (path.resolve(process.argv[1] ?? '') === __filename) {
  await main();
}
