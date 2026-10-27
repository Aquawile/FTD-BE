// Serves the built web app and proxies /api/* to the backend, the way nginx does on the web VM.
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(process.env.E2E_DIST ?? path.join(here, "../../context/figma_prototype/dist"));
const port = Number(process.env.E2E_PORT ?? 5174);
const api = new URL(process.env.E2E_API ?? "http://127.0.0.1:8080");
const types = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml", ".json": "application/json", ".png": "image/png", ".ico": "image/x-icon", ".woff2": "font/woff2" };

http.createServer((req, res) => {
  if (req.url.startsWith("/api/")) {
    const upstream = http.request({ host: api.hostname, port: api.port, method: req.method, path: req.url.slice(4), headers: { ...req.headers, host: api.host } }, r => {
      res.writeHead(r.statusCode ?? 502, r.headers);
      r.pipe(res);
    });
    upstream.on("error", () => { res.writeHead(502); res.end("api unreachable"); });
    req.pipe(upstream);
    return;
  }
  const clean = decodeURIComponent(req.url.split("?")[0]);
  let file = path.join(root, clean);
  if (!file.startsWith(root) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) file = path.join(root, "index.html");
  res.writeHead(200, { "content-type": types[path.extname(file)] ?? "application/octet-stream" });
  fs.createReadStream(file).pipe(res);
}).listen(port, "127.0.0.1", () => console.log(`serving ${root} on http://127.0.0.1:${port} (api -> ${api.origin})`));
