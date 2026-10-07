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

import { fromDescribe, parseEnvFile } from './run.js';

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
