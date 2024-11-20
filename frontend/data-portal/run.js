#!/usr/bin/env node

import { spawnSync } from 'child_process';
import fs from 'fs';
import yaml from 'js-yaml';
import path from 'path';
import { fileURLToPath } from 'url';

const NAME = 'data-portal';
const DEV_MODE = process.argv.slice(2).includes('--dev');
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

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
  const specificSettingsPath = DEV_MODE ? `.devcontainer/${NAME}.yaml` : `${NAME}.yaml`;

  let specificSettings = {};
  try {
    specificSettings = yaml.load(fs.readFileSync(specificSettingsPath, 'utf8'));
  } catch (e) {
    if (e.code !== 'ENOENT') throw e; // ignore non-existing file
  }

  // Merge the default and specific settings
  const settings = { ...defaultSettings, ...specificSettings };

  // Override settings with environment variables
  const prefix = NAME.replace('-', '_');
  for (const key in settings) {
    if (!settings.hasOwnProperty(key)) continue;
    const envVarName = `${prefix}_${key}`;
    const value = settings[key];
    let envVarValue = process.env[envVarName];
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
  const outputDir = DEV_MODE ? 'public' : getBrowserDir('dist');

  // Ensure the output directory exists
  if (!fs.existsSync(outputDir)) {
    throw new Error(`Output directory not found: ${outputDir}`);
  }

  const configPath = path.join(outputDir, 'config.js');
  const configScript = `window.config = ${JSON.stringify(settings)}`;
  fs.writeFileSync(configPath, configScript, 'utf8');
}

/**
 * Get the name and IP address of the specified URL.
 */
function getNameAndAddress(url) {
  const { hostname } = new URL(url);
  if (!hostname) {
    console.error(`Invalid URL: ${url}`);
  }
  const result = spawnSync('dig', ['+short', hostname, '@8.8.8.8'], {
    encoding: 'utf8',
  });
  const address = result.error ? null : result.stdout.trim();
  if (!address) {
    console.error(`Cannot resolve ${hostname}`);
    process.exit(1);
  }
  return [hostname, address];
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

  if (baseUrl === `http://${host}:${port}`) {
    console.log('Using the mock service worker for API calls.');
    basicAuth = null;
  } else if (baseUrl.startsWith('https://')) {
    console.log(`Using ${baseUrl} as backend for API calls via proxy.`);
    const [baseName, baseIp] = getNameAndAddress(baseUrl);
    addHostEntry(baseName, baseIp);
    console.log(`Your host computer should resolve ${baseName} to ${host}.`);
    port = 443;
    ssl = true;
  } else {
    console.error(`Invalid base URL: ${baseUrl}`);
    process.exit(1);
  }

  // export settings used in the proxy config
  process.env.data_portal_base_url = baseUrl;
  if (basicAuth) {
    process.env.data_portal_basic_auth = basicAuth;
  } else {
    delete process.env.data_portal_basic_auth;
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

  const distDir = getBrowserDir(path.join(__dirname, 'dist'));
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
  ];
  if (ssl) {
    params.push('--http2', '--http2-tls-cert', sslCert, '--http2-tls-key', sslKey);
  }
  params.push('./index.html');

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
  console.log('Runtime settings =', settings);

  const {
    host,
    port,
    ssl,
    ssl_cert,
    ssl_key,
    log_level: logLevel,
    base_url: baseUrl,
    basic_auth: basicAuth,
  } = settings;

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

  writeSettings(settings);

  (DEV_MODE ? runDevServer : runProdServer)(
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
