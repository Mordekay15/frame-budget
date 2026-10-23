// Where the simulator's answers come from. Every decider has the same method,
// `decide(spell) -> Promise<answer>`, so the architectures can't tell them apart.
//
//   fake     no network: the corpus label (with a little noise) or the keyword
//            rules, after a latency drawn from a latency model. For developing
//            and testing; never thesis data.
//   live     the real Jev. Records every answer and latency, so the run can be replayed.
//   replay   answers and latencies from a recording, so a live run can be repeated
//            exactly, for free, as often as needed.

import fs from "node:fs";
import path from "node:path";
import { rulesDecide } from "../src/engine/rules.js";
import { rng } from "../src/engine/rng.js";
import { ELEMENTS } from "../src/engine/spells.js";
import { JevClient, PRICE_PER_M_INPUT_TOKENS, TIMEOUT_MS } from "../lib/jev.mjs";

// ---------------------------------------------------------------- latency models

/** Synthetic: lognormal, fitted to the Step 0 measurement of 12 Oct (median 310 ms, p95 506 ms). */
export class LognormalLatency {
  constructor({ medianMs = 310, sigma = 0.3, seed = 0 } = {}) {
    this.r = rng(seed + 101);
    Object.assign(this, { medianMs, sigma });
  }
  sample() { return this.r.lognormal(this.medianMs, this.sigma); }
  describe() { return `synthetic lognormal (median ${this.medianMs} ms)`; }
}

/** Resamples measured latencies (warm requests) from one or more Step 0 CSVs. */
export class EmpiricalLatency {
  constructor(pattern, { seed = 0, condition = "warm" } = {}) {
    this.files = expand(pattern);
    this.values = [];
    for (const f of this.files) {
      for (const row of readCsv(f)) {
        if ((row.condition ?? condition) !== condition) continue;
        this.values.push(row.ok === "1" ? +row.latency_ms : Infinity); // a failure never arrives
      }
    }
    if (!this.values.length) throw new Error(`no '${condition}' rows in ${pattern}`);
    this.r = rng(seed + 202);
  }
  sample() { return this.values[this.r.int(this.values.length)]; }
  describe() { return `measured, ${this.values.length} requests from ${this.files.map((f) => path.basename(f)).join(", ")}`; }
}

/** 'synthetic', or a CSV path/glob. 'measured' = this folder's Step 0 runs if any, else synthetic. */
export function latencyModel(spec = "measured", seed = 0) {
  if (spec === "measured") spec = expand("results/step0/jev_spell_latency*.csv").length ? "results/step0/jev_spell_latency*.csv" : "synthetic";
  return spec === "synthetic" ? new LognormalLatency({ seed }) : new EmpiricalLatency(spec, { seed });
}

// ---------------------------------------------------------------- deciders

// The grading request is about 3 times longer than the old difficulty request; this
// is an estimate until Step 0 measures the real count (input_tokens in the CSV).
const estimateTokens = (spell) => 720 + Math.ceil(spell.length / 4);

export class FakeDecider {
  constructor({ corpus = [], latency = new LognormalLatency(), seed = 0, noise = 0.08 } = {}) {
    this.labels = new Map(corpus.map((c) => [c.text, c]));
    this.latency = latency;
    this.r = rng(seed + 303);
    this.noise = noise;
    this.name = "fake";
  }
  async decide(spell) {
    const ms = this.latency.sample();
    if (!Number.isFinite(ms)) return { ok: false, error: "timeout", latencyMs: TIMEOUT_MS };
    const label = this.labels.get(spell);
    let decision = label ? { element: label.element, target: label.target, power: label.power } : rulesDecide(spell);
    if (this.r() < this.noise) decision = { ...decision, element: ELEMENTS[this.r.int(ELEMENTS.length - 1)] };
    const inputTokens = estimateTokens(spell);
    return { ok: true, valid: true, decision, latencyMs: ms, inputTokens, cost: (inputTokens * PRICE_PER_M_INPUT_TOKENS) / 1e6 };
  }
  close() {}
}

export class LiveDecider {
  constructor({ recordDir = null } = {}) {
    this.client = new JevClient();
    this.recordDir = recordDir;
    this.recording = {};
    this.name = "live";
  }
  async decide(spell) {
    const r = await this.client.decide(spell);
    const kept = { ok: r.ok, valid: r.valid, decision: r.decision, latencyMs: r.latencyMs, inputTokens: r.inputTokens,
                   cost: r.cost, error: r.error, httpStatus: r.httpStatus };
    (this.recording[spell] ||= []).push(kept);
    return kept;
  }
  close() {
    this.client.close();
    if (this.recordDir) {
      fs.mkdirSync(this.recordDir, { recursive: true });
      fs.writeFileSync(path.join(this.recordDir, "answers.json"), JSON.stringify(this.recording, null, 1));
    }
  }
}

/** The k-th request for a spell gets the k-th recorded answer, so the same seeds replay exactly. */
export class ReplayDecider {
  constructor(dir, { fallbackLatency = new LognormalLatency() } = {}) {
    this.recording = JSON.parse(fs.readFileSync(path.join(dir, "answers.json"), "utf8"));
    this.seen = new Map();
    this.misses = 0;
    this.fallbackLatency = fallbackLatency;
    this.name = "replay";
  }
  reset() { this.seen.clear(); }
  async decide(spell) {
    const list = this.recording[spell];
    if (!list?.length) {
      // a spell the recording never saw (a different partial text while typing, say):
      // answered by the rules, and counted, so the summary shows how complete the replay was
      this.misses += 1;
      return { ok: true, valid: true, decision: rulesDecide(spell), latencyMs: this.fallbackLatency.sample(),
               inputTokens: estimateTokens(spell), cost: 0, replayMiss: true };
    }
    const k = this.seen.get(spell) || 0;
    this.seen.set(spell, k + 1);
    return { ...list[Math.min(k, list.length - 1)] };
  }
  close() {}
}

// ---------------------------------------------------------------- small file helpers

export function expand(pattern) {
  if (!pattern.includes("*")) return fs.existsSync(pattern) ? [pattern] : [];
  const dir = path.dirname(pattern), base = path.basename(pattern);
  if (!fs.existsSync(dir)) return [];
  const re = new RegExp("^" + base.replace(/[.+^${}()|[\]\\]/g, "\\$&").replace(/\*/g, ".*") + "$");
  return fs.readdirSync(dir).filter((f) => re.test(f)).sort().map((f) => path.join(dir, f));
}

/** A small CSV reader (quoted fields, doubled quotes). Returns objects keyed by the header. */
export function readCsv(file) {
  const text = fs.readFileSync(file, "utf8");
  const rows = [];
  let row = [], field = "", q = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (q) {
      if (ch === '"' && text[i + 1] === '"') { field += '"'; i++; }
      else if (ch === '"') q = false;
      else field += ch;
    } else if (ch === '"') q = true;
    else if (ch === ",") { row.push(field); field = ""; }
    else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && text[i + 1] === "\n") i++;
      row.push(field); field = "";
      if (row.length > 1 || row[0] !== "") rows.push(row);
      row = [];
    } else field += ch;
  }
  if (field || row.length) { row.push(field); rows.push(row); }
  const [head, ...body] = rows;
  return body.map((r) => Object.fromEntries(head.map((h, i) => [h, r[i] ?? ""])));
}

export function writeCsv(file, rows) {
  if (!rows.length) return;
  const cols = Object.keys(rows[0]);
  const cell = (v) => {
    const s = v === null || v === undefined ? "" : typeof v === "object" ? JSON.stringify(v) : String(v);
    return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, [cols.join(","), ...rows.map((r) => cols.map((c) => cell(r[c])).join(","))].join("\n") + "\n");
}

export function loadCorpus(file = new URL("../data/spells.json", import.meta.url)) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}
