// Run the game locally without Vercel: `npm run dev`, then open http://localhost:3000.
// Serves the static files and routes /api/decide to the same handler Vercel runs.
// The API key is read from text-game/.env (see .env.example).

import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import handler from "./api/decide.js";

const PORT = +process.env.PORT || 3000;
const ROOT = path.dirname(fileURLToPath(import.meta.url));
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript", ".css": "text/css",
                ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png" };

http.createServer(async (req, res) => {
  const url = new URL(req.url, "http://localhost");
  if (url.pathname === "/api/decide") {
    const chunks = [];
    for await (const c of req) chunks.push(c);
    const raw = Buffer.concat(chunks).toString();
    try { req.body = raw ? JSON.parse(raw) : {}; } catch { req.body = {}; }
    return handler(req, res);
  }
  const rel = url.pathname === "/" ? "index.html" : decodeURIComponent(url.pathname).replace(/^\/+/, "");
  const file = path.resolve(ROOT, rel);
  // only files inside the game folder, and never the server-side code or the key
  if (!file.startsWith(ROOT + path.sep) || /^(api|lib|sim|test|\.env)/.test(rel) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    res.statusCode = 404;
    return res.end("not found");
  }
  res.setHeader("Content-Type", TYPES[path.extname(file)] || "application/octet-stream");
  fs.createReadStream(file).pipe(res);
}).listen(PORT, () => console.log(`Spell game on http://localhost:${PORT}`));
