#!/usr/bin/env node

/**
 * Run the development or production server for the data portal.
 *
 * Syntax: run.js [--dev [--with-backend] [--with-oidc]]
 */

import { spawnSync } from 'child_process';
import fs from 'fs';
import yaml from 'js-yaml';
import path from 'path';
import { fileURLToPath } from 'url';

const NAME = 'data-portal';
const DEFAULT_BACKEND = 'https://data.staging.ghga.dev';

const args = process.argv.slice(1);
const DEV = args.includes('--dev');
const WITH_BACKEND = args.includes('--with-backend');
const WITH_OIDC = args.includes('--with-oidc');

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Set the version from package.json in the ribbon text.
 */
function setVersion(settings) {
  const text = settings.ribbon_text;
  if (!text || !text.includes('$v')) return;
  const packageJsonPath = path.join(__dirname, 'package.json');
  const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
  settings.ribbon_text = text.replace('$v', packageJson.version || '?');
}

/**
 * Reads and merges configuration settings from default and specific YAML files.
 * Overrides settings with environment variables prefixed with the application name.
 *
 * @returns {Object} The merged configuration settings.
 * @throws {Error} If there is an error reading the configuration files.
 */
function readSettings() {
  // Read the default configuration file
  const defaultSettingsPath = path.join(__dirname, `${NAME}.default.yaml`);
  const defaultSettings = yaml.load(fs.readFileSync(defaultSettingsPath, 'utf8'));

  // Read the (optional) development or production specific configuration file
  const specificSettingsPath = DEV ? `.devcontainer/${NAME}.yaml` : `${NAME}.yaml`;

  let specificSettings = {};
  try {
    specificSettings = yaml.load(fs.readFileSync(specificSettingsPath, 'utf8'));
  } catch (e) {
    if (e.code !== 'ENOENT') throw e; // ignore non-existing file
  }

  // Merge the default and specific settings
  const settings = { ...defaultSettings, ...specificSettings };

  // Override settings with environment variables
  // (the env var name must be fully lower case or upper case, but not mixed)
  const prefix = NAME.replace('-', '_');
  for (const key in settings) {
    if (!settings.hasOwnProperty(key)) continue;
    const envVarName = `${prefix}_${key}`;
    const value = settings[key];
    let envVarValue = process.env[envVarName] ?? process.env[envVarName.toUpperCase()];
    if (envVarValue === undefined) continue;
    const isObject = typeof value === 'object' && value !== null;
    if (isObject) {
      envVarValue = JSON.parse(envVarValue);
    } else {
      const isBoolean = typeof value === 'boolean';
      if (isBoolean) {
        envVarValue = envVarValue.toLowerCase() === 'true';
      } else {
        const isNumber = typeof value === 'number';
        if (isNumber) {
          envVarValue = parseFloat(envVarValue);
        }
      }
    }

    settings[key] = envVarValue;
  }

  return settings;
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
 * Write the settings into the config file in the appropriate output directory.
 *
 * @param {Object} settings - The configuration settings to write.
 * @throws {Error} If the output directory does not exist.
 */
function writeSettings(settings) {
  const outputDir = DEV ? 'public' : getBrowserDir('dist');

  // Ensure the output directory exists
  if (!fs.existsSync(outputDir)) {
    throw new Error(`Output directory not found: ${outputDir}`);
  }

  const configPath = path.join(outputDir, 'config.js');
  const configScript = `window.config = ${JSON.stringify(settings)};`;
  fs.writeFileSync(configPath, configScript, 'utf8');
}

/**
 * Find the IP address for a given hostname
 */
function getIpAddress(hostname) {
  const result = spawnSync('dig', ['+short', hostname, '@8.8.8.8'], {
    encoding: 'utf8',
  });
  const address = result.error ? null : result.stdout.trim();
  if (!address) {
    console.error(`Cannot resolve ${hostname}`);
    process.exit(1);
  }
  return address;
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
function runDevServer(host, port, ssl, sslCert, sslKey, logLevel, baseUrl, basicAuth) {
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
    const ipAddress = getIpAddress(hostname);
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
  if (logLevel == 'debug') {
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
function main() {
  process.chdir(__dirname);

  const settings = readSettings();

  let {
    host,
    port,
    ssl,
    ssl_cert,
    ssl_key,
    log_level: logLevel,
    base_url: baseUrl,
    basic_auth: basicAuth,
  } = settings;

  setVersion(settings);

  let msg = 'Running';
  let adapted = false;
  if (DEV) {
    msg += ' in development mode';
    if (WITH_BACKEND || WITH_OIDC) {
      if (
        !baseUrl ||
        baseUrl.startsWith('http://127.') ||
        baseUrl.startsWith('http://localhost')
      ) {
        settings.base_url = baseUrl = DEFAULT_BACKEND;
        adapted = true;
      }
    }
    if (WITH_BACKEND) {
      msg += ` with ${baseUrl.split('://')[1] || baseUrl} as backend`;
    } else {
      msg += ' with mock API';
    }
    if (WITH_OIDC) {
      msg += ' and authentication via OIDC';
      if (settings.port !== 443 || !settings.ssl) {
        settings.port = port = 443;
        settings.ssl = ssl = true;
        adapted = true;
      }
    } else {
      msg += ' and mock authentication';
    }
  } else {
    msg += ' in production mode';
  }
  console.log(msg);
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

  delete settings.host;
  delete settings.port;
  delete settings.ssl;
  delete settings.ssl_cert;
  delete settings.ssl_key;
  delete settings.log_level;
  delete settings.basic_auth;

  if (DEV) {
    settings.mock_api = !WITH_BACKEND;
    settings.mock_oidc = !WITH_OIDC;
  }

  writeSettings(settings);

  (DEV ? runDevServer : runProdServer)(
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

main();
