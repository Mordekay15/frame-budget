// The decision layer: who decides what a spell does, and when.
//
// A "decision point" is the moment the player presses Enter. The spell charges
// for at most `deadlineMs`; whatever decision is in hand when it is ready is cast.
//
//   rules     the keyword parser decides at once. The baseline.
//   blocking  ask Jev and wait inside the tick: the game freezes. Built to be measured.
//   async     ask Jev in the background; cast Jev's answer if it arrives within the
//             deadline, otherwise cast the rules' decision. The game never stalls.
//   cache     as async, but look the spell's signature up first. A hit casts at once.
//             Every answer is stored, even one that came too late to be used.
//   prefetch  as cache, but while the player types, every pause sends the text typed
//             so far. If the player then submits that text, the answer is already
//             there or on its way, with a head start of the pause.
//
// The channel carries requests without blocking: submit() now, poll() every tick.
// The browser's channel uses fetch; the simulator's uses the simulated clock.
// Times are in milliseconds on whatever clock the caller uses.

import { rulesDecide } from "./rules.js";
import { signature } from "./signature.js";

export const MODES = ["rules", "blocking", "async", "cache", "prefetch"];

export class DecisionLayer {
  constructor({ mode, channel, deadlineMs = 200, coarse = 1, cache = new Map(), debounceMs = 250, onCast = () => {} }) {
    if (!MODES.includes(mode)) throw new Error(`unknown mode ${mode}`);
    this.mode = mode;
    this.channel = channel;
    this.deadlineMs = deadlineMs;
    this.coarse = coarse;
    this.cache = cache;
    this.debounceMs = debounceMs;
    this.onCast = onCast;
    this.events = [];
    this.pending = null;
    this.nextReq = 0;
    this.byReq = new Map();      // decision request id -> its event, to log late answers
    this.inflight = new Map();   // prefetch: signature -> request id
    this.prefetched = new Set(); // signatures whose answer came from a prefetch
    this.typed = "";
    this.lastKeyAt = 0;
    this.lastPrefetchKey = null;
    this.counts = { requests: 0, prefetchRequests: 0, prefetchUsed: 0, tokens: 0, cost: 0,
                    late: 0, failed: 0, hits: 0 };
  }

  get busy() { return this.pending !== null; }

  onTyping(text, now) {
    this.typed = text;
    this.lastKeyAt = now;
  }

  /** Enter was pressed. Returns false if a spell is still charging. May return a
   *  Promise (blocking mode in the simulator); the caller must wait for it. */
  onSubmit(text, now) {
    if (this.pending || !text.trim()) return false;
    const ev = { n: this.events.length + 1, text, submittedAt: now, rules: rulesDecide(text),
                 source: null, requested: false, latencyMs: null, late: false, failed: false, freezeMs: 0 };
    this.events.push(ev);
    this.typed = "";
    this.lastPrefetchKey = null;
    this.pending = ev;

    if (this.mode === "rules") return this._resolve(ev.rules, "rules", now), true;

    if (this.mode === "blocking") {
      ev.requested = true;
      this.counts.requests += 1;
      const done = (r) => {
        this._count(r);
        ev.latencyMs = ev.freezeMs = r.latencyMs;
        if (r.ok) this._resolve(r.decision, "jev", now, r.latencyMs);
        else { ev.failed = true; this.counts.failed += 1; this._resolve(ev.rules, "rules", now, r.latencyMs); }
        return true;
      };
      const r = this.channel.blocking(text);
      return typeof r.then === "function" ? r.then(done) : done(r);
    }

    if (this.mode === "cache" || this.mode === "prefetch") {
      const key = (ev.key = signature(text, this.coarse));
      if (this.cache.has(key)) {
        const fromPrefetch = this.mode === "prefetch" && this.prefetched.has(key);
        // A prefetched answer counts as a prefetch the first time; reusing it later is a cache hit.
        if (fromPrefetch) { this.counts.prefetchUsed += 1; this.prefetched.delete(key); } else this.counts.hits += 1;
        return this._resolve(this.cache.get(key), fromPrefetch ? "prefetch" : "cache", now), true;
      }
      if (this.mode === "prefetch" && this.inflight.has(key)) {
        ev.waitingFor = key; // a prefetch for exactly this text is already on its way
        return true;
      }
    }
    this._send(ev, text, now);
    return true;
  }

  onTick(now) {
    for (const arr of this.channel.poll(now)) this._arrival(arr, now);

    if (this.mode === "prefetch" && this.typed.trim() && now - this.lastKeyAt >= this.debounceMs) {
      const key = signature(this.typed, this.coarse);
      if (key !== this.lastPrefetchKey && !this.cache.has(key) && !this.inflight.has(key)) {
        const id = ++this.nextReq;
        this.inflight.set(key, id);
        this.counts.prefetchRequests += 1;
        this.channel.submit(id, this.typed, now, { kind: "prefetch", key });
      }
      this.lastPrefetchKey = key;
    }

    // 1 ms of tolerance, so a deadline written as 167 ms means 5 ticks of 33.3 ms, not 6
    const ev = this.pending;
    if (ev && now - ev.submittedAt >= this.deadlineMs - 1) this._resolve(ev.rules, "rules", now);
  }

  _send(ev, text, now) {
    const id = ++this.nextReq;
    ev.requested = true;
    ev.reqId = id;
    this.byReq.set(id, ev);
    this.counts.requests += 1;
    this.channel.submit(id, text, now, { kind: "decision", key: ev.key });
  }

  _count(r) {
    this.counts.tokens += r.inputTokens || 0;
    this.counts.cost += r.cost || 0;
  }

  _arrival(arr, now) {
    const r = arr.answer;
    this._count(r);
    const { kind, key } = arr.tag;
    if (r.ok && key !== undefined && (this.mode === "cache" || this.mode === "prefetch") && !this.cache.has(key)) {
      this.cache.set(key, r.decision);
      if (kind === "prefetch") this.prefetched.add(key);
    }
    if (kind === "prefetch") {
      this.inflight.delete(key);
      const ev = this.pending;
      if (ev && ev.waitingFor === key) {
        ev.requested = true;
        ev.latencyMs = arr.arrivedAt - arr.sentAt;
        if (r.ok) { this.counts.prefetchUsed += 1; this.prefetched.delete(key); this._resolve(r.decision, "prefetch", now); }
        else { ev.failed = true; this.counts.failed += 1; this._resolve(ev.rules, "rules", now); }
      }
      return;
    }
    const ev = this.byReq.get(arr.id);
    this.byReq.delete(arr.id);
    if (!ev) return;
    ev.latencyMs = arr.arrivedAt - arr.sentAt;
    if (!r.ok) { ev.failed = true; this.counts.failed += 1; }
    if (this.pending === ev) {
      if (r.ok) this._resolve(r.decision, "jev", now);
      else this._resolve(ev.rules, "rules", now);
    } else if (r.ok) {
      ev.late = true;
      this.counts.late += 1;
    }
  }

  _resolve(decision, source, now, waitMs = now - this.pending.submittedAt) {
    const ev = this.pending;
    this.pending = null;
    ev.source = source;
    ev.decision = decision;
    ev.waitMs = waitMs;
    ev.fallback = source === "rules";
    this.onCast(decision, ev);
  }
}
