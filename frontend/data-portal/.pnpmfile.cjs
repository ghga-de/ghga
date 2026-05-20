/**
 * pnpm hook file for dependency overrides
 * Handles security patches for transitive dependencies pulled in by @compodoc/compodoc
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

function readPackage(pkg) {
  // Override vulnerable versions in @angular-devkit/core@21.1.0
  // This is required until @compodoc/compodoc updates its @angular-devkit dependency
  if (pkg.name === '@angular-devkit/core' && pkg.version === '21.1.0') {
    pkg.dependencies ||= {};
    // picomatch: upgrade from 4.0.3 (vulnerable) to 4.0.4
    pkg.dependencies.picomatch = '4.0.4';
    // ajv: upgrade from 8.17.1 (ReDoS vulnerability) to >=8.18.0
    pkg.dependencies.ajv = '>=8.18.0';
  }

  return pkg;
}

module.exports = {
  hooks: {
    readPackage,
  },
  // Force uuid to >=14.0.0 to patch buffer bounds check vulnerability (GHSA-w5hq-g745-h8pq)
  // until @compodoc/compodoc updates its dependencies
  overrides: {
    'uuid': '>=14.0.0',
  },
};
