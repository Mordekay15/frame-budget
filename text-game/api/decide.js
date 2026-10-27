// Vercel serverless function: POST /api/decide {"spell": "..."} -> Jev's typed answer.
//
// The browser can't call Jev directly: the API key must stay on the server. This
// function adds the server's own hop, so the latency the browser sees is Jev's
// latency (`latencyMs`, measured here) plus the trip to Vercel and back. The
// simulator calls Jev directly and measures Jev alone.
//
// Set TYPESAFE_API_KEY (or OPENROUTER_API_KEY) in the Vercel project's environment variables.

import { JevClient, detectProvider } from "../lib/jev.mjs";
import { MAX_SPELL_CHARS } from "../src/engine/spells.js";

let client = null; // reused while the function instance stays warm, so the connection stays open

// A light per-instance limit, so a public link can't be used to run up the bill.
const PER_MINUTE = 60;
const seen = new Map();

function send(res, status, body) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Cache-Control", "no-store");
  res.end(JSON.stringify(body));
}

export default async function handler(req, res) {
  if (req.method === "GET") return send(res, 200, { ok: true, provider: detectProvider() });
  if (req.method !== "POST") return send(res, 405, { ok: false, error: "use POST" });

  const ip = String(req.headers["x-forwarded-for"] || "local").split(",")[0].trim();
  const now = Date.now();
  const recent = (seen.get(ip) || []).filter((t) => now - t < 60_000);
  if (recent.length >= PER_MINUTE) return send(res, 429, { ok: false, error: "too many spells, wait a minute" });
  seen.set(ip, [...recent, now]);

  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch { body = {}; } }
  const spell = String(body?.spell ?? "").slice(0, MAX_SPELL_CHARS);
  if (!spell.trim()) return send(res, 400, { ok: false, error: "empty spell" });

  try {
    client ??= new JevClient();
  } catch (err) {
    return send(res, 503, { ok: false, error: err.message });
  }
  const r = await client.decide(spell);
  const { raw, ...out } = r; // the raw answers stay on the server
  return send(res, r.ok ? 200 : 502, out);
}
