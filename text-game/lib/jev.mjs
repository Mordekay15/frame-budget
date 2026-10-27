// A small Node client for Jev (TypeSafe):
//
//   TypeSafe directly (default)                  OpenRouter
//   POST https://api.typesafe.ai/v1/systemone    POST https://openrouter.ai/api/alpha/decisions
//   {"model": "jev-1.13.0", ...}                 {"model": "typesafe/jev-1.13", ...}
//
// Used by the Vercel function (api/decide.js), the simulator's live mode and the
// Step 0 measurement. It keeps one HTTPS connection open between requests, the way
// a game server would; `fresh: true` opens a new one to measure the cold case.
// Only Node's standard library is used.

import http from "node:http";
import https from "node:https";
import fs from "node:fs";
import path from "node:path";
import { QUESTIONS, parseAnswers, stateText } from "../src/engine/spells.js";

// Model ids are pinned, so results don't move when "latest" points to a new release.
export const PROVIDERS = {
  typesafe: { host: "api.typesafe.ai", path: "/v1/systemone", model: "jev-1.13.0", keyEnv: "TYPESAFE_API_KEY" },
  openrouter: { host: "openrouter.ai", path: "/api/alpha/decisions", model: "typesafe/jev-1.13", keyEnv: "OPENROUTER_API_KEY" },
};
export const PRICE_PER_M_INPUT_TOKENS = 0.042; // USD; output tokens are free (Oct 2026)
export const TIMEOUT_MS = 5000;

let dotenv = null;
function setting(name) {
  if (process.env[name]?.trim()) return process.env[name].trim();
  if (dotenv === null) {
    dotenv = {};
    // text-game/.env first, then the repo root's .env (where the key was kept for the first bench)
    for (const p of [path.resolve(".env"), path.resolve("..", ".env")]) {
      if (!fs.existsSync(p)) continue;
      for (const line of fs.readFileSync(p, "utf8").split(/\r?\n/)) {
        const m = line.match(/^\s*([A-Z_]+)\s*=\s*(.*)\s*$/);
        if (m && !(m[1] in dotenv)) dotenv[m[1]] = m[2].replace(/^["']|["']$/g, "");
      }
    }
  }
  return (dotenv[name] || "").trim();
}

export function detectProvider() {
  const chosen = setting("JEV_PROVIDER").toLowerCase();
  if (chosen) {
    if (!PROVIDERS[chosen]) throw new Error(`JEV_PROVIDER must be typesafe or openrouter, not ${chosen}`);
    return chosen;
  }
  for (const [name, p] of Object.entries(PROVIDERS)) if (setting(p.keyEnv)) return name;
  return null;
}

export class JevClient {
  // `baseUrl` points the client at another server (the tests use a local mock).
  constructor({ provider = detectProvider(), timeoutMs = TIMEOUT_MS, baseUrl = null, key = null } = {}) {
    if (!provider) {
      throw new Error("No API key. Put TYPESAFE_API_KEY=... (or OPENROUTER_API_KEY=...) in text-game/.env or the environment.");
    }
    this.provider = provider;
    this.cfg = PROVIDERS[provider];
    this.key = key ?? setting(this.cfg.keyEnv);
    if (!this.key) throw new Error(`JEV_PROVIDER=${provider}, but ${this.cfg.keyEnv} is not set.`);
    this.timeoutMs = timeoutMs;
    const u = new URL(baseUrl ?? (setting("JEV_BASE_URL") || `https://${this.cfg.host}${this.cfg.path}`));
    this.transport = u.protocol === "http:" ? http : https;
    this.target = { hostname: u.hostname, port: u.port || undefined, path: u.pathname };
    this.agent = new this.transport.Agent({ keepAlive: true, maxSockets: 8 });
  }

  /** One request, timed around the HTTP call only. Never throws. */
  decide(spell, { fresh = false } = {}) {
    const payload = JSON.stringify({ model: this.cfg.model, state: stateText(spell), questions: QUESTIONS });
    return new Promise((resolve) => {
      const t0 = performance.now();
      const done = (fields) => resolve({ latencyMs: performance.now() - t0, ok: false, valid: false, httpStatus: 0,
                                         error: "", decision: null, inputTokens: 0, outputTokens: 0, cost: 0,
                                         provider: this.provider, ...fields });
      const req = this.transport.request({
        ...this.target, method: "POST",
        agent: fresh ? false : this.agent, timeout: this.timeoutMs,
        headers: { Authorization: `Bearer ${this.key}`, "Content-Type": "application/json",
                   "Content-Length": Buffer.byteLength(payload) },
      }, (res) => {
        const chunks = [];
        res.on("data", (c) => chunks.push(c));
        res.on("end", () => {
          const latencyMs = performance.now() - t0;
          const raw = Buffer.concat(chunks).toString();
          let body;
          try { body = JSON.parse(raw); } catch { return done({ latencyMs, httpStatus: res.statusCode, error: raw.slice(0, 200) }); }
          if (res.statusCode !== 200 || body.error) {
            return done({ latencyMs, httpStatus: res.statusCode, error: JSON.stringify(body.error ?? body).slice(0, 300) });
          }
          const usage = body.usage || {};
          const inputTokens = +usage.input_tokens || 0;
          // OpenRouter reports the cost; TypeSafe reports tokens only, so compute it.
          const cost = usage.cost != null ? +usage.cost : (inputTokens * PRICE_PER_M_INPUT_TOKENS) / 1e6;
          const base = { latencyMs, httpStatus: 200, inputTokens, outputTokens: +usage.output_tokens || 0, cost,
                         servedModel: body.model || "", provider: body.provider || this.provider, raw: body.answers };
          try {
            const { decision, conf, probs } = parseAnswers(body);
            resolve({ ...base, ok: true, valid: true, error: "", decision, conf, probs });
          } catch (err) {
            // A 200 whose answers don't fit the schema: the case Jev claims never happens.
            done({ ...base, error: `invalid answer: ${err.message}`.slice(0, 300) });
          }
        });
      });
      req.on("timeout", () => req.destroy(new Error(`timeout after ${this.timeoutMs} ms`)));
      req.on("error", (err) => done({ error: `${err.name}: ${err.message}` }));
      req.end(payload);
    });
  }

  close() {
    this.agent.destroy();
  }
}
