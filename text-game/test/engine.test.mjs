import { test } from "node:test";
import assert from "node:assert/strict";
import { rulesDecide } from "../src/engine/rules.js";
import { signature } from "../src/engine/signature.js";
import { parseAnswers, QUESTIONS, ELEMENTS, TARGETS, POWERS } from "../src/engine/spells.js";
import { Game, TICK_MS } from "../src/engine/game.js";
import { DecisionLayer } from "../src/engine/arch.js";

test("rules read keywords, and miss poetry", () => {
  assert.deepEqual(rulesDecide("A blizzard freezes every one of them"), { element: "frost", target: "all", power: "medium" });
  assert.equal(rulesDecide("protect the house with a stone wall").target, "shield");
  assert.equal(rulesDecide("Make it remember the longest January night").element, "fizzle");
  assert.equal(rulesDecide("asdf").power, "weak");
});

test("signatures get coarser", () => {
  assert.notEqual(signature("Fire, a big ball!", 0), signature("fire a big ball", 0));
  assert.equal(signature("Fire, a big ball!", 1), signature("fire a big  ball", 1));
  assert.equal(signature("a big ball of fire", 2), signature("Fire, big ball!", 2));
});

test("questions cover every allowed answer, and parsing rejects others", () => {
  assert.deepEqual(Object.keys(QUESTIONS.element.criteria), ELEMENTS);
  assert.deepEqual(Object.keys(QUESTIONS.target.criteria), TARGETS);
  assert.deepEqual(Object.keys(QUESTIONS.power.criteria), POWERS);
  const body = { answers: { element: { choice: "fire", confidence: 0.9 }, target: { choice: "all" }, power: { choice: "mighty" } } };
  assert.deepEqual(parseAnswers(body).decision, { element: "fire", target: "all", power: "mighty" });
  assert.throws(() => parseAnswers({ answers: { ...body.answers, power: { choice: "ultra" } } }));
});

test("weaknesses double damage, resistances halve it", () => {
  const g = new Game({ seed: 1 });
  g.enemies.push({ id: 1, kind: "ember", x: 0.5, lane: 0, hp: 100, maxHp: 100, speed: 0 });
  g.cast({ element: "frost", target: "nearest", power: "medium" });
  g.cast({ element: "fire", target: "nearest", power: "medium" });
  assert.equal(g.enemies[0].hp, 100 - 56 - 14);
});

// A channel whose answers arrive after a fixed delay, to test the layer alone.
function fixedChannel(latencyMs, decision = { element: "light", target: "all", power: "strong" }) {
  const q = [];
  return {
    sent: 0,
    submit(id, text, now, tag) { this.sent++; q.push({ id, tag, sentAt: now, arrivedAt: now + latencyMs, answer: { ok: true, decision, inputTokens: 700, cost: 1e-5 } }); },
    poll(now) { const out = q.filter((a) => a.arrivedAt <= now); q.splice(0, q.length, ...q.filter((a) => a.arrivedAt > now)); return out; },
    blocking() { return { ok: true, decision, latencyMs }; },
  };
}
function drive(layer, from, to) { for (let t = from; t <= to; t += TICK_MS) layer.onTick(t); }

test("async: in time casts Jev, late casts the rules and counts the late answer", () => {
  for (const [lat, source, late] of [[200, "jev", 0], [600, "rules", 1]]) {
    const casts = [];
    const layer = new DecisionLayer({ mode: "async", channel: fixedChannel(lat), deadlineMs: 350, onCast: (d, ev) => casts.push(ev) });
    layer.onSubmit("a warm glow", 0);
    drive(layer, 0, 1000);
    assert.equal(casts.length, 1);
    assert.equal(casts[0].source, source);
    assert.equal(layer.counts.late, late);
  }
});

test("cache: a late answer is still stored, and the next identical spell is instant", () => {
  const casts = [];
  const ch = fixedChannel(600);
  const layer = new DecisionLayer({ mode: "cache", channel: ch, deadlineMs: 350, onCast: (d, ev) => casts.push(ev) });
  layer.onSubmit("A warm glow!", 0);
  drive(layer, 0, 1000);
  layer.onSubmit("a warm glow", 1100);
  assert.deepEqual(casts.map((e) => e.source), ["rules", "cache"]);
  assert.equal(casts[1].waitMs, 0);
  assert.equal(ch.sent, 1);
});

test("prefetch: a pause while typing sends the text early, and Enter uses it", () => {
  const casts = [];
  const ch = fixedChannel(300);
  const layer = new DecisionLayer({ mode: "prefetch", channel: ch, deadlineMs: 250, debounceMs: 250, onCast: (d, ev) => casts.push(ev) });
  layer.onTyping("a warm glow", 0);
  drive(layer, 0, 280); // the pause: the prefetch goes out at ~267 ms
  assert.equal(ch.sent, 1);
  layer.onSubmit("a warm glow", 400); // Enter, before the answer is back (it arrives at ~567 ms)
  drive(layer, 400, 1000);
  assert.equal(casts[0].source, "prefetch");
  assert.ok(casts[0].waitMs < 300, `waited ${casts[0].waitMs}`);
  assert.equal(ch.sent, 1);
});

test("blocking reports the freeze", () => {
  const casts = [];
  const layer = new DecisionLayer({ mode: "blocking", channel: fixedChannel(420), onCast: (d, ev) => casts.push(ev) });
  layer.onSubmit("sunbeam", 0);
  assert.equal(casts[0].source, "jev");
  assert.equal(casts[0].freezeMs, 420);
});

test("one spell at a time", () => {
  const layer = new DecisionLayer({ mode: "async", channel: fixedChannel(300) });
  assert.equal(layer.onSubmit("fire", 0), true);
  assert.equal(layer.onSubmit("ice", 10), false);
});

test("a deadline of 167 ms is 5 ticks: an answer at 160 ms is in time, one at 170 ms is not", () => {
  for (const [lat, source] of [[160, "jev"], [170, "rules"]]) {
    const casts = [];
    const layer = new DecisionLayer({ mode: "async", channel: fixedChannel(lat), deadlineMs: 167, onCast: (d, ev) => casts.push(ev) });
    layer.onSubmit("a warm glow", 0);
    drive(layer, 0, 400);
    assert.equal(casts[0].source, source);
    assert.ok(Math.abs(casts[0].waitMs - 5 * TICK_MS) < 1e-6, `waited ${casts[0].waitMs}`);
  }
});
