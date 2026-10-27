// One simulated game on a simulated clock: exactly 33.3 ms per tick, no real time.
//
// A request "arrives" at send time + its latency, wherever that latency came from
// (a latency model, the live Jev, a recording). With the same seeds, the same game
// happens: the bot, the gloomlings and the arrivals all repeat.
//
// Blocking is the one architecture that stops the clock: the tick that sends the
// request lasts as long as the request, and the game then catches up with
// back-to-back updates, during which the player can't react.

import { Game, TICK_MS } from "../src/engine/game.js";
import { DecisionLayer } from "../src/engine/arch.js";
import { Bot } from "./bot.mjs";

const MAX_GAME_MS = 15 * 60 * 1000;

export class SimChannel {
  constructor(decider) {
    this.decider = decider;
    this.queue = [];
    this.waiting = [];
  }
  submit(id, text, now, tag) {
    this.waiting.push(this.decider.decide(text).then((answer) => {
      this.queue.push({ id, tag, sentAt: now, arrivedAt: now + answer.latencyMs, answer });
    }));
  }
  /** Wait (in real time) for live requests to come back; simulated time is unaffected. */
  async settle() {
    if (!this.waiting.length) return;
    await Promise.all(this.waiting);
    this.waiting = [];
    this.queue.sort((a, b) => a.arrivedAt - b.arrivedAt || a.id - b.id);
  }
  poll(now) {
    let k = 0;
    while (k < this.queue.length && this.queue[k].arrivedAt <= now) k++;
    return this.queue.splice(0, k);
  }
  blocking(text) { return this.decider.decide(text); }
}

const quantile = (xs, q) => {
  if (!xs.length) return null;
  const s = [...xs].sort((a, b) => a - b);
  return s[Math.min(s.length - 1, Math.floor(q * s.length))];
};

export async function simulateGame({ mode, deadlineMs, skill, seed, decider, corpus, coarse = 1, cache = new Map() }) {
  const game = new Game({ seed });
  const bot = new Bot(skill, seed * 7919 + 13, corpus);
  const channel = new SimChannel(decider);
  const layer = new DecisionLayer({
    mode, channel, deadlineMs, coarse, cache,
    onCast: (d, ev) => {
      const res = game.cast(d);
      bot.feedback(ev.text, res);
      ev.castAt = game.timeMs;
      ev.hits = res.hits.length;
      ev.doubled = res.hits.filter((h) => h.mult > 1).length;
    },
  });

  let now = 0, worstTickMs = TICK_MS, overruns = 0;
  while (!game.over && now < MAX_GAME_MS) {
    let tickMs = TICK_MS;
    for (const a of bot.tick(now, game, layer.busy)) {
      if (a.type === "type") layer.onTyping(a.text, now);
      else {
        const r = layer.onSubmit(a.text, now);
        if (r && typeof r.then === "function") {
          await r;
          const freeze = layer.events.at(-1).freezeMs;
          // the frozen tick, then the catch-up updates
          tickMs += freeze;
          for (let k = 0; k < Math.floor(freeze / TICK_MS); k++) game.update(TICK_MS);
          now += freeze;
        }
      }
    }
    await channel.settle();
    game.update(TICK_MS);
    layer.onTick(now);
    worstTickMs = Math.max(worstTickMs, tickMs);
    if (tickMs > TICK_MS * 1.5) overruns += 1;
    now += TICK_MS;
  }
  // answers still in flight at the end are counted for cost, like a real game would pay
  await channel.settle();
  for (const arr of channel.poll(Infinity)) layer._count(arr.answer);

  const evs = layer.events.filter((e) => e.source);
  for (const e of evs) {
    const lab = bot.label(e.text);
    e.label = lab;
    e.correct = lab ? e.decision.element === lab.element : null;
    e.rulesCorrect = lab ? e.rules.element === lab.element : null;
  }
  const labelled = evs.filter((e) => e.label);
  const share = (f, list = evs) => (list.length ? list.filter(f).length / list.length : null);
  const c = layer.counts;
  const minutes = now / 60000;
  return {
    summary: {
      arch: mode, deadline_ms: mode === "rules" || mode === "blocking" ? "" : deadlineMs, skill, seed,
      decider: decider.name, coarse: mode === "cache" || mode === "prefetch" ? coarse : "",
      spells: evs.length,
      model_share: share((e) => e.source !== "rules"),
      from_jev: share((e) => e.source === "jev"),
      from_cache: share((e) => e.source === "cache"),
      from_prefetch: share((e) => e.source === "prefetch"),
      fallback_rate: share((e) => e.source === "rules"),
      late: c.late, failed: c.failed,
      mean_wait_ms: evs.length ? evs.reduce((s, e) => s + e.waitMs, 0) / evs.length : null,
      p95_wait_ms: quantile(evs.map((e) => e.waitMs), 0.95),
      requests: c.requests, prefetch_requests: c.prefetchRequests, prefetch_used: c.prefetchUsed, cache_hits: c.hits,
      tokens: c.tokens, cost_usd: c.cost, minutes, cost_per_hour_usd: minutes ? (c.cost / minutes) * 60 : 0,
      element_accuracy: share((e) => e.correct, labelled),
      rules_element_accuracy: share((e) => e.rulesCorrect, labelled),
      waves: game.wave, kills: game.kills, hearts: game.hearts, won: game.won ? 1 : 0,
      worst_tick_ms: worstTickMs, tick_overruns: overruns,
      replay_misses: decider.misses ?? "",
    },
    events: evs.map((e) => ({
      arch: mode, deadline_ms: deadlineMs, skill, seed, n: e.n, submitted_ms: Math.round(e.submittedAt), text: e.text,
      source: e.source, wait_ms: Math.round(e.waitMs), latency_ms: e.latencyMs === null ? "" : Math.round(e.latencyMs),
      late: e.late ? 1 : 0, failed: e.failed ? 1 : 0,
      element: e.decision.element, target: e.decision.target, power: e.decision.power,
      rules_element: e.rules.element, rules_target: e.rules.target, rules_power: e.rules.power,
      label_element: e.label?.element ?? "", label_target: e.label?.target ?? "", correct: e.correct === null ? "" : e.correct ? 1 : 0,
      hits: e.hits, doubled: e.doubled,
    })),
  };
}
