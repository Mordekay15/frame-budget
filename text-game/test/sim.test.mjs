import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { simulateGame } from "../sim/simulate.mjs";
import { FakeDecider, LognormalLatency, ReplayDecider, loadCorpus, writeCsv, readCsv } from "../sim/deciders.mjs";
import { analyze, SAME_SPELLS } from "../sim/measure.mjs";
import { run } from "../sim/run.mjs";

const corpus = loadCorpus();
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), "tg-"));

test("the corpus is labelled with allowed values", async () => {
  const { ELEMENTS, TARGETS, POWERS } = await import("../src/engine/spells.js");
  for (const c of corpus) {
    assert.ok(ELEMENTS.includes(c.element) && TARGETS.includes(c.target) && POWERS.includes(c.power), c.text);
    assert.ok(["good", "ok", "bad"].includes(c.quality), c.text);
  }
  for (const s of SAME_SPELLS) assert.ok(corpus.some((c) => c.text === s), s);
});

test("the same seeds give the same game", async () => {
  const once = async () => {
    const decider = new FakeDecider({ corpus, latency: new LognormalLatency({ seed: 4 }), seed: 4 });
    const { events } = await simulateGame({ mode: "prefetch", deadlineMs: 250, skill: "average", seed: 9, decider, corpus });
    return JSON.stringify(events);
  };
  assert.equal(await once(), await once());
});

test("only blocking breaks the tick budget", async () => {
  for (const mode of ["rules", "blocking", "async", "cache", "prefetch"]) {
    const decider = new FakeDecider({ corpus, seed: 2 });
    const { summary } = await simulateGame({ mode, deadlineMs: 350, skill: "strong", seed: 3, decider, corpus });
    assert.ok(summary.spells > 10, `${mode}: ${summary.spells} spells`);
    if (mode === "blocking") assert.ok(summary.worst_tick_ms > 100);
    else assert.ok(summary.worst_tick_ms < 34, `${mode}: ${summary.worst_tick_ms}`);
  }
});

test("a replay of a recording reproduces the run", async () => {
  const dir = tmp();
  // record with the fake decider standing in for the live one
  const fake = new FakeDecider({ corpus, seed: 5 });
  const recording = {};
  const recorder = { name: "live", decide: async (s) => { const a = await fake.decide(s); (recording[s] ||= []).push(a); return a; }, close() {} };
  const a = await simulateGame({ mode: "async", deadlineMs: 350, skill: "average", seed: 11, decider: recorder, corpus });
  fs.writeFileSync(path.join(dir, "answers.json"), JSON.stringify(recording));
  const b = await simulateGame({ mode: "async", deadlineMs: 350, skill: "average", seed: 11, decider: new ReplayDecider(dir), corpus });
  assert.deepEqual(b.events, a.events);
  assert.equal(b.summary.replay_misses, 0);
});

test("the runner writes its files", async () => {
  const out = tmp();
  const { games } = await run({ arch: "cache", deadline: 250, skill: "weak", games: 2, seed: 1, coarse: 1, decider: "fake",
                                latency: "synthetic", sweep: false, quiet: true, out });
  assert.equal(games.length, 2);
  for (const f of ["games.csv", "spells.csv", "summary.md", "meta.json"]) assert.ok(fs.existsSync(path.join(out, f)), f);
  assert.equal(readCsv(path.join(out, "games.csv")).length, 2);
});

test("the Step 0 analysis reads a measurement file", () => {
  const dir = tmp();
  const rows = [];
  for (const [condition, text, lat, ok] of [["warm", corpus[0].text, 240, 1], ["warm", corpus[5].text, 330, 1], ["cold", corpus[2].text, 0, 0],
                                            ["same", SAME_SPELLS[0], 250, 1], ["same", SAME_SPELLS[0], 260, 1]]) {
    rows.push({ condition, i: 1, started_at: "2026-10-23T10:00:00Z", latency_ms: lat, ok, valid: ok, http_status: ok ? 200 : 0, error: ok ? "" : "timeout",
                input_tokens: 760, output_tokens: 0, cost: 3.2e-5, served_model: "jev-1.13.0", provider: "typesafe",
                element: "frost", target: "nearest", power: "medium", words: 5, chars: text.length,
                label_element: corpus.find((c) => c.text === text)?.element ?? "", label_target: "nearest", label_power: "", rules_element: "frost", rules_target: "nearest", rules_power: "medium", text });
  }
  writeCsv(path.join(dir, "jev_spell_latency_x.csv"), rows);
  const md = analyze(path.join(dir, "jev_spell_latency*.csv"));
  assert.match(md, /\| warm \| 2 \| 0 \| 0 \|/);
  assert.match(md, /\| cold \| 1 \| 1 \|/);
  assert.match(md, /Format validity:\*\* 4 of 4/);
});
