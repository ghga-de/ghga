// Proxy configuration for the Angular development server

const baseUrl = process.env.data_portal_base_url;
const basicAuth = process.env.data_portal_basic_auth;
const checkCert = !process.env.data_portal_ignore_cert;
const mockApi = !process.env.data_portal_with_backend;
const mockOidc = !process.env.data_portal_with_oidc;

// filter out standard headers
function filterHeaders(headers) {
  return Object.entries(headers).reduce((acc, [key, value]) => {
    // show only custom headers
    if (!/x-/.test(key)) return acc;
    acc[key] = value;
    return acc;
  }, {});
}

// log headers
function logHeaders(headers) {
  const out = [];
  for (const [key, value] of Object.entries(headers)) {
    out.push(`${key}: ${value}`);
  }
  console.log(out.join('\n'));
}

// configure proxy
function configure(proxy) {
  proxy.on('proxyReq', (proxyReq, req, res) => {
    console.log('\n', '==>', req.method, req.url);
    logHeaders(filterHeaders(proxyReq.getHeaders()));
  });
  proxy.on('proxyRes', (proxyRes, req, res) => {
    console.log('\n', '<==', req.method, req.url);
    console.log('Status:', proxyRes.statusCode, proxyRes.statusMessage);
    logHeaders(filterHeaders(proxyRes.headers));
  });
}

let target = baseUrl || 'http://127.0.0.1';
if (!target.endsWith('/')) target += '/';
const useProxy = (!mockApi || !mockOidc) && !target.startsWith('http://127.');

const config = {};

if (useProxy) {
  const targetHost = new URL(target).hostname;
  if (!/^(\.\d{1,3}){4}$/.test(targetHost)) {
    try {
      const hostsFile = '/etc/hosts';
      const fs = await import('fs');
      const hostsContent = await fs.promises.readFile(hostsFile, 'utf8');
      const lines = hostsContent.split('\n');
      const hostEntry = lines.find((line) => line.includes(targetHost));
      if (hostEntry) {
        const resolvedAddress = hostEntry.split(/\s+/)[0];
        console.log(
          `The target hostname ${targetHost} resolves to ${resolvedAddress} using the hosts file.`,
        );
      } else {
        console.log(
          `The target hostname ${targetHost} is not found in the hosts file.`,
        );
        console.warn('Please check the hosts file in the dev container!');
      }
      const dns = await import('dns');
      const addresses = await dns.promises.lookup(targetHost);
      const resolvedAddress = addresses.address;
      if (resolvedAddress.startsWith('127.')) {
        console.log(
          `The target hostname ${targetHost} resolves to a local address on the host computer.`,
        );
      } else {
        console.log(
          `The target hostname ${targetHost} resolves to ${resolvedAddress} on the host computer.`,
        );
        if (!mockOidc) {
          console.warn('Please check the hosts file on your host computer!');
        }
      }
    } catch (err) {
      console.warn(`Cannot resolve ${targetHost}:`, err);
    }
  }

  console.log(`\nRunning proxy server with target: ${target}`);
  if (basicAuth) {
    console.log('Using basic authentication');
  }
  config['/api'] = {
    target,
    changeOrigin: true,
    secure: checkCert,
    auth: basicAuth,
    logLevel: 'debug',
    configure,
  };
  config['/.well-known'] = {
    target,
    changeOrigin: true,
    secure: checkCert,
    logLevel: 'debug',
    configure,
  };
}

if (!mockOidc && baseUrl && !baseUrl.startsWith('http://127.')) {
  console.log(`\n\x1b[33mPlease point your browser to: ${baseUrl}\x1b[0m\n`);
}

export default config;
