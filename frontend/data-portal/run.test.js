/**
 * Tests for the pure functions of the run.js launcher, run by `pnpm test` through node:test
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { after, describe, test } from 'node:test';

import {
  adaptSettings,
  applyEnv,
  browserConfig,
  fromDescribe,
  parseEnvFile,
} from './run.js';

describe('fromDescribe', () => {
  // the same cases as scripts/tests/test_platform_version.py, which tests the original
  const cases = [
    ['ghga/15.3.1', '15.3.1'],
    ['ghga/15.3.1-rc.8', '15.3.1-rc.8'],
    ['ghga/15.3.1-dirty', '15.3.1+dirty'],
    ['ghga/15.3.1-rc.8-71-g44594f5', '15.3.1-rc.8+dev.71.44594f5'],
    ['ghga/15.3.1-rc.8-71-g44594f5c-dirty', '15.3.1-rc.8+dev.71.44594f5c.dirty'],
    ['v1.0.0', '0.0.0+dev'],
    ['', '0.0.0+dev'],
  ];
  for (const [described, expected] of cases) {
    test(`${described || '(empty)'} -> ${expected}`, () => {
      assert.equal(fromDescribe(described), expected);
    });
  }
});

describe('parseEnvFile', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'run-test-'));
  after(() => fs.rmSync(dir, { recursive: true }));

  const parse = (content) => {
    const file = path.join(dir, '.env');
    fs.writeFileSync(file, content);
    return parseEnvFile(file);
  };

  test('skips blank lines, comments and lines without =', () => {
    assert.deepEqual(parse('\n# comment\n  \nno_equals\nkey=value\n'), {
      key: 'value',
    });
  });

  test('drops an export prefix and trims around key and value', () => {
    assert.deepEqual(parse('export key = value \n'), { key: 'value' });
  });

  test('expands escapes in double quotes only', () => {
    assert.deepEqual(parse('a="x\\ty\\n\\"z\\""\nb=\'x\\ty\'\n'), {
      a: 'x\ty\n"z"',
      b: 'x\\ty',
    });
  });

  test('keeps inner whitespace of quoted values and the = in values', () => {
    assert.deepEqual(parse('a=" x "\nb=k=v\n'), { a: ' x ', b: 'k=v' });
  });

  test('keeps an unmatched quote as part of the value', () => {
    assert.deepEqual(parse('a="x\n'), { a: '"x' });
  });

  test('returns nothing for a missing file', () => {
    assert.deepEqual(parseEnvFile(path.join(dir, 'missing.env')), {});
  });
});

describe('applyEnv', () => {
  const defaults = () => ({
    port: 8080,
    ssl: false,
    base_url: 'http://127.0.0.1:8080',
    oidc_scope: null,
    ribbon: { text: 'Dev' },
  });

  test('converts to the type of the setting it overrides', () => {
    const env = {
      data_portal_port: '443',
      data_portal_ssl: 'TRUE',
      data_portal_base_url: 'https://example.org',
      data_portal_oidc_scope: 'openid',
      data_portal_ribbon: '{"text": "Test"}',
    };
    assert.deepEqual(applyEnv(defaults(), env, {}), {
      port: 443,
      ssl: true,
      base_url: 'https://example.org',
      oidc_scope: 'openid',
      ribbon: { text: 'Test' },
    });
  });

  test('takes the environment over the .env file, lower before upper case', () => {
    const settings = applyEnv(
      defaults(),
      { data_portal_port: '1', DATA_PORTAL_PORT: '2', DATA_PORTAL_SSL: 'true' },
      { data_portal_port: '3', data_portal_ssl: 'false', DATA_PORTAL_BASE_URL: 'x' },
    );
    assert.equal(settings.port, 1);
    assert.equal(settings.ssl, true);
    assert.equal(settings.base_url, 'x');
  });

  test('ignores mixed case and variables for unknown settings', () => {
    const settings = applyEnv(
      defaults(),
      { Data_Portal_Port: '1', data_portal_unknown: 'x' },
      {},
    );
    assert.deepEqual(settings, defaults());
  });
});

describe('adaptSettings', () => {
  const local = () => ({ base_url: 'http://localhost:8080', port: 8080, ssl: false });

  test('leaves production settings alone', () => {
    const settings = local();
    assert.deepEqual(adaptSettings(settings, { dev: false }), {
      message: 'Running in production mode',
      adapted: false,
    });
    assert.deepEqual(settings, local());
  });

  test('keeps a local base URL with the mock API', () => {
    const settings = local();
    const { message, adapted } = adaptSettings(settings, { dev: true });
    assert.equal(
      message,
      'Running in development mode with mock API and mock authentication',
    );
    assert.equal(adapted, false);
    assert.deepEqual(settings, local());
  });

  test('replaces a local base URL with a backend, keeps a remote one', () => {
    const settings = local();
    const mode = { dev: true, withBackend: true };
    assert.equal(adaptSettings(settings, mode).adapted, true);
    assert.equal(settings.base_url, 'https://data.staging.ghga.dev');

    const remote = { ...local(), base_url: 'https://example.org' };
    const { message, adapted } = adaptSettings(remote, mode);
    assert.equal(adapted, false);
    assert.equal(
      message,
      'Running in development mode with example.org as backend and mock authentication',
    );
  });

  test('switches to HTTPS on port 443 for OIDC', () => {
    const settings = { ...local(), base_url: 'https://example.org' };
    const { message, adapted } = adaptSettings(settings, { dev: true, withOidc: true });
    assert.equal(adapted, true);
    assert.equal(settings.port, 443);
    assert.equal(settings.ssl, true);
    assert.match(message, /with mock API and authentication via OIDC$/);
  });
});

describe('browserConfig', () => {
  const settings = {
    host: '0.0.0.0',
    port: 443,
    ssl: true,
    ssl_cert: 'cert.pem',
    ssl_key: 'key.pem',
    log_level: 'info',
    basic_auth: 'user:secret',
    root_files: { 'robots.txt': '' },
    base_url: 'https://example.org',
    version: '15.3.1',
  };

  test('leaves out what only the server needs, the basic auth included', () => {
    assert.deepEqual(browserConfig(settings, { dev: false }), {
      base_url: 'https://example.org',
      version: '15.3.1',
    });
  });

  test('adds the mock flags in development', () => {
    const config = browserConfig(settings, { dev: true, withBackend: true });
    assert.equal(config.mock_api, false);
    assert.equal(config.mock_oidc, true);
    assert.equal(config.basic_auth, undefined);
  });
});
