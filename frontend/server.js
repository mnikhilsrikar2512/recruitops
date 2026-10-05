const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = Number(process.env.PORT || 4174);
const API_PORT = process.env.API_PORT || 8000;
const ROOT = path.resolve(__dirname);
const MIME = {
  '.html': 'text/html', '.css': 'text/css', '.js': 'application/javascript',
  '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg',
  '.webp': 'image/webp', '.avif': 'image/avif',
  '.svg': 'image/svg+xml', '.ico': 'image/x-icon',
};

function proxyApi(req, res) {
  const proxyReq = http.request(
    { host: '127.0.0.1', port: API_PORT, path: req.url, method: req.method, headers: { ...req.headers, host: `127.0.0.1:${API_PORT}` } },
    (proxyRes) => {
      res.writeHead(proxyRes.statusCode, proxyRes.headers);
      proxyRes.pipe(res);
    },
  );
  proxyReq.on('error', () => {
    res.writeHead(503, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ detail: 'Backend is unreachable. Start the API server and try again.' }));
  });
  req.pipe(proxyReq);
}

http.createServer((req, res) => {
  if (req.url.startsWith('/api/')) {
    proxyApi(req, res);
    return;
  }
  let urlPath;
  try {
    urlPath = decodeURIComponent(req.url.split('?')[0]);
  } catch {
    res.writeHead(400); res.end('Bad request'); return;
  }
  // Resolve inside ROOT only — "/../backend/.env" must never be served.
  const inRoot = (candidate) => candidate === ROOT || candidate.startsWith(ROOT + path.sep);
  let filePath = path.resolve(ROOT, '.' + (urlPath === '/' ? '/index.html' : urlPath));
  if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
    filePath = path.resolve(ROOT, 'pages', '.' + urlPath);
  }
  if (!fs.existsSync(filePath)) {
    // Try appending .html
    filePath = filePath.endsWith('.html') ? filePath : filePath + '.html';
  }
  if (!inRoot(filePath) || !fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
    res.writeHead(404); res.end('Not found'); return;
  }
  const ext = path.extname(filePath);
  const headers = {
    'Content-Type': MIME[ext] || 'application/octet-stream',
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'same-origin',
    'X-Frame-Options': 'SAMEORIGIN',
  };
  const isAsset = ext === '.css' || ext === '.js';
  const cacheAssets = process.env.NODE_ENV === 'production';
  if (ext === '.html' || (isAsset && !cacheAssets)) {
    headers['Cache-Control'] = 'no-store, no-cache, must-revalidate';
    headers['Pragma'] = 'no-cache';
  } else if (isAsset) {
    headers['Cache-Control'] = 'public, max-age=31536000, immutable';
  }
  res.writeHead(200, headers);
  fs.createReadStream(filePath).pipe(res);
}).listen(PORT, () => console.log(`Frontend: http://localhost:${PORT} (API proxied to :${API_PORT})`));
