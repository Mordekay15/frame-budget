// Step 0 for the spell game: measure Jev on the grading request, in isolation.
//
//   node sim/measure.mjs                     all conditions, then the summary
//   node sim/measure.mjs --warm 50 --cold 0 --same 5 --long 0 --inject 0    a quick trial
//   node sim/measure.mjs --analyze "results/step0/jev_spell_latency*.csv"   pool earlier runs
//
// Conditions (same idea as the first Step 0, adapted to free text):
//   warm     random corpus spells on one reused connection: how the game calls Jev
//   cold     a new connection for every request: the cost of the handshake
//   same     3 fixed spells (clear, poetic, borderline), repeated: consistency
//   long     two corpus spells joined (~40 to 70 words): does input length cost time?
//   inject   spells that try to give the game orders: does the format hold, and the grade?
//
// Every request is a CSV row, failures included. `valid` = the answer parsed into
// the schema: Joonas's "deterministic", the guaranteed output format.
// Runs on your own machine (this needs your API key and your network).

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { JevClient } from "../lib/jev.mjs";
import { rulesDecide, words } from "../src/engine/rules.js";
import { rng } from "../src/engine/rng.js";
import { expand, loadCorpus, readCsv, writeCsv } from "./deciders.mjs";

export const DEADLINES = [33, 100, 167, 200, 233, 333, 500];
export const SAME_SPELLS = [
  "Freeze the nearest gloomling solid",                                   // clear, keywords
  "Make it remember the longest January night, when even the stars shivered", // poetic, no frost keyword
  "Remind it of the first warm morning in May",                           // borderline: light? fire? nature?
];
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function parseArgs(argv) {
  const o = { warm: 300, cold: 100, same: 30, long: 50, inject: 10, pause: 200, seed: 1 };
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i].replace(/^--/, "");
    if (k === "analyze") o.analyze = argv[++i];
    else if (k === "out") o.out = argv[++i];
    else if (k in o) o[k] = +argv[++i];
    else throw new Error(`unknown option ${argv[i]} (see the top of sim/measure.mjs)`);
  }
  return o;
}

async function measure(o) {
  const corpus = loadCorpus();
  const label = new Map(corpus.map((c) => [c.text, c]));
  const r = rng(o.seed);
  const good = corpus.filter((c) => c.quality === "good");
  const injections = corpus.filter((c) => c.probe === "injection");
  const plan = [];
  for (let i = 0; i < o.warm; i++) plan.push(["warm", r.pick(corpus).text, false]);
  for (let i = 0; i < o.cold; i++) plan.push(["cold", r.pick(corpus).text, true]);
  for (const s of SAME_SPELLS) for (let i = 0; i < o.same; i++) plan.push(["same", s, false]);
  for (let i = 0; i < o.long; i++) plan.push(["long", `${r.pick(good).text}, and then ${r.pick(good).text.toLowerCase()}`, false]);
  for (const s of injections) for (let i = 0; i < o.inject; i++) plan.push(["inject", s.text, false]);

  const client = new JevClient();
  console.log(`${plan.length} requests to ${client.provider} (${client.cfg.model}), ${o.pause} ms apart.`);
  await client.decide("warm-up spell"); // opens the connection; not recorded
  const rows = [];
  const counter = {};
  for (const [condition, text, fresh] of plan) {
    counter[condition] = (counter[condition] || 0) + 1;
    const startedAt = new Date().toISOString();
    const a = await client.decide(text, { fresh });
    const lab = label.get(text);
    const ru = rulesDecide(text);
    rows.push({
      condition, i: counter[condition], started_at: startedAt, latency_ms: a.latencyMs.toFixed(2),
      ok: a.ok ? 1 : 0, valid: a.valid ? 1 : 0, http_status: a.httpStatus, error: a.error,
      input_tokens: a.inputTokens, output_tokens: a.outputTokens, cost: a.cost,
      served_model: a.servedModel ?? "", provider: a.provider,
      element: a.decision?.element ?? "", target: a.decision?.target ?? "", power: a.decision?.power ?? "",
      element_conf: a.conf?.element ?? "", target_conf: a.conf?.target ?? "", power_conf: a.conf?.power ?? "",
      element_probs: a.probs?.element ?? "", target_probs: a.probs?.target ?? "", power_probs: a.probs?.power ?? "",
      words: words(text).length, chars: text.length,
      label_element: lab?.element ?? "", label_target: lab?.target ?? "", label_power: lab?.power ?? "",
      rules_element: ru.element, rules_target: ru.target, rules_power: ru.power,
      text,
    });
    if (rows.length % 25 === 0) process.stdout.write(`\r${rows.length}/${plan.length}`);
    await sleep(o.pause);
  }
  process.stdout.write("\n");
  client.close();
  const stamp = new Date().toISOString().replace(/[-:]/g, "").replace("T", "_").slice(0, 13);
  const file = o.out ?? path.join("results", "step0", `jev_spell_latency_${stamp}.csv`);
  writeCsv(file, rows);
  console.log(`Written ${file}`);
  return file;
}

// ---------------------------------------------------------------- analysis

const q = (xs, p) => { const s = [...xs].sort((a, b) => a - b); return s.length ? s[Math.min(s.length - 1, Math.floor(p * s.length))] : NaN; };
const f0 = (x) => (Number.isFinite(x) ? x.toFixed(0) : "–");
const pc = (a, b) => (b ? `${((100 * a) / b).toFixed(0)}%` : "–");

export function analyze(pattern) {
  const files = expand(pattern);
  if (!files.length) throw new Error(`no files match ${pattern}`);
  const rows = files.flatMap((f) => readCsv(f).map((r) => ({ ...r, file: path.basename(f) })));
  const out = [`# Step 0 (spell game): Jev on the grading request`, "",
               `Pooled from ${files.length} run(s): ${files.map((f) => path.basename(f)).join(", ")}. ${rows.length} requests.`, ""];

  out.push("## Latency by condition", "",
    "| condition | n | errors | invalid | median | p95 | p99 | max | " + DEADLINES.map((d) => `≤ ${d} ms`).join(" | ") + " |",
    "|---|---|---|---|---|---|---|---|" + DEADLINES.map(() => "---|").join(""));
  for (const c of ["warm", "cold", "same", "long", "inject"]) {
    const rs = rows.filter((r) => r.condition === c);
    if (!rs.length) continue;
    const okLat = rs.filter((r) => r.ok === "1").map((r) => +r.latency_ms);
    const errors = rs.filter((r) => r.ok !== "1").length;
    const invalid = rs.filter((r) => r.http_status === "200" && r.valid !== "1").length;
    // failures count as misses: they never arrive in time
    const under = DEADLINES.map((d) => pc(okLat.filter((x) => x <= d).length, rs.length));
    out.push(`| ${c} | ${rs.length} | ${errors} | ${invalid} | ${f0(q(okLat, 0.5))} | ${f0(q(okLat, 0.95))} | ${f0(q(okLat, 0.99))} | ${f0(Math.max(...okLat))} | ${under.join(" | ")} |`);
  }

  const ok = rows.filter((r) => r.ok === "1");
  const http200 = rows.filter((r) => r.http_status === "200");
  out.push("", `**Format validity:** ${http200.filter((r) => r.valid === "1").length} of ${http200.length} answered requests parsed into the schema (${pc(http200.filter((r) => r.valid === "1").length, http200.length)}).`, "");

  out.push("## Does length cost time? (warm and long)", "", "| words | n | median latency | median input tokens |", "|---|---|---|---|");
  const buckets = [[0, 5], [6, 15], [16, 30], [31, 999]];
  for (const [lo, hi] of buckets) {
    const rs = ok.filter((r) => (r.condition === "warm" || r.condition === "long") && +r.words >= lo && +r.words <= hi);
    if (rs.length) out.push(`| ${lo}–${hi === 999 ? "…" : hi} | ${rs.length} | ${f0(q(rs.map((r) => +r.latency_ms), 0.5))} ms | ${f0(q(rs.map((r) => +r.input_tokens), 0.5))} |`);
  }

  out.push("", "## Consistency (same spell, repeated)", "", "| spell | n | element | target | power |", "|---|---|---|---|---|");
  const mode = (xs) => { const m = {}; for (const x of xs) m[x] = (m[x] || 0) + 1; const [k, n] = Object.entries(m).sort((a, b) => b[1] - a[1])[0] || ["–", 0]; return `${k} ${pc(n, xs.length)}`; };
  for (const text of [...new Set(ok.filter((r) => r.condition === "same").map((r) => r.text))]) {
    const rs = ok.filter((r) => r.condition === "same" && r.text === text);
    out.push(`| ${text} | ${rs.length} | ${mode(rs.map((r) => r.element))} | ${mode(rs.map((r) => r.target))} | ${mode(rs.map((r) => r.power))} |`);
  }

  const lab = ok.filter((r) => r.label_element && (r.condition === "warm" || r.condition === "cold"));
  out.push("", "## Agreement with the corpus labels (warm and cold)", "",
    `Element: Jev ${pc(lab.filter((r) => r.element === r.label_element).length, lab.length)}, keyword rules ${pc(lab.filter((r) => r.rules_element === r.label_element).length, lab.length)}. ` +
    `Target: Jev ${pc(lab.filter((r) => r.target === r.label_target).length, lab.length)}, rules ${pc(lab.filter((r) => r.rules_target === r.label_target).length, lab.length)}. (${lab.length} labelled requests.)`);

  const inj = ok.filter((r) => r.condition === "inject");
  if (inj.length) {
    out.push("", "## Spells that try to give orders", "", "| spell | n | element | power |", "|---|---|---|---|");
    for (const text of [...new Set(inj.map((r) => r.text))]) {
      const rs = inj.filter((r) => r.text === text);
      out.push(`| ${text} | ${rs.length} | ${mode(rs.map((r) => r.element))} | ${mode(rs.map((r) => r.power))} |`);
    }
  }

  const tok = ok.map((r) => +r.input_tokens), cost = ok.map((r) => +r.cost);
  out.push("", "## Cost", "", `Median ${f0(q(tok, 0.5))} input tokens per request; mean cost $${(cost.reduce((a, b) => a + b, 0) / (cost.length || 1)).toExponential(2)} per request.`);

  out.push("", "## Runs", "", "| file | first request | warm median | warm ≤ 200 ms |", "|---|---|---|---|");
  for (const f of files.map((x) => path.basename(x))) {
    const rs = rows.filter((r) => r.file === f && r.condition === "warm");
    const lat = rs.filter((r) => r.ok === "1").map((r) => +r.latency_ms);
    out.push(`| ${f} | ${rows.find((r) => r.file === f)?.started_at ?? ""} | ${f0(q(lat, 0.5))} ms | ${pc(lat.filter((x) => x <= 200).length, rs.length)} |`);
  }
  return out.join("\n") + "\n";
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const o = parseArgs(process.argv.slice(2));
    const pattern = o.analyze ?? (await measure(o), "results/step0/jev_spell_latency*.csv");
    const md = analyze(pattern);
    fs.mkdirSync("results/step0", { recursive: true });
    fs.writeFileSync("results/step0/summary.md", md);
    console.log(md);
  } catch (err) {
    console.error(err.message);
    process.exit(1);
  }
}
