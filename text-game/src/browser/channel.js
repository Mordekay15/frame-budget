// How the browser reaches Jev. Same interface as the simulator's channel:
// submit() and poll() never block; blocking() does, on purpose.

import { rulesDecide } from "../engine/rules.js";
import { rng } from "../engine/rng.js";

const TIMEOUT_MS = 5000;

/** Through our Vercel function, /api/decide. The key never reaches the browser. */
export class FetchChannel {
  constructor(url = "/api/decide") {
    this.url = url;
    this.arrived = [];
  }

  submit(id, text, now, tag) {
    const t0 = performance.now();
    const ctl = new AbortController();
    const timer = setTimeout(() => ctl.abort(), TIMEOUT_MS);
    const deliver = (answer) => {
      clearTimeout(timer);
      this.arrived.push({ id, tag, sentAt: now, arrivedAt: now + (performance.now() - t0), answer });
    };
    fetch(this.url, { method: "POST", headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ spell: text }), signal: ctl.signal })
      .then((r) => r.json())
      .then((b) => deliver({ ...b, serverMs: b.latencyMs }))
      .catch((err) => deliver({ ok: false, error: String(err) }));
  }

  poll() {
    const out = this.arrived;
    this.arrived = [];
    return out;
  }

  /** A synchronous request: the whole page freezes until Jev answers. That is the point. */
  blocking(text) {
    const t0 = performance.now();
    const xhr = new XMLHttpRequest();
    try {
      xhr.open("POST", this.url, false);
      xhr.setRequestHeader("Content-Type", "application/json");
      xhr.send(JSON.stringify({ spell: text }));
      const b = JSON.parse(xhr.responseText);
      return { ...b, serverMs: b.latencyMs, latencyMs: performance.now() - t0 };
    } catch (err) {
      return { ok: false, error: String(err), latencyMs: performance.now() - t0 };
    }
  }
}

/**
 * No server, no key: the keyword rules answer, after a delay drawn from the
 * measured Jev latency (lognormal, median 310 ms). Good for trying the game and
 * the architectures; it is not Jev, so its "understanding" is only the rules'.
 */
export class OfflineChannel {
  constructor(seed = 7) {
    this.r = rng(seed);
    this.inflight = [];
  }

  _answer(text) {
    return { ok: true, decision: rulesDecide(text), inputTokens: 0, cost: 0, latencyMs: this.r.lognormal(310, 0.3) };
  }

  submit(id, text, now, tag) {
    const answer = this._answer(text);
    this.inflight.push({ id, tag, sentAt: now, arrivedAt: now + answer.latencyMs, answer });
  }

  poll(now) {
    const ready = this.inflight.filter((a) => a.arrivedAt <= now);
    this.inflight = this.inflight.filter((a) => a.arrivedAt > now);
    return ready;
  }

  blocking(text) {
    const answer = this._answer(text);
    const end = performance.now() + answer.latencyMs;
    while (performance.now() < end) { /* freeze, like a real blocking call */ }
    return answer;
  }
}
