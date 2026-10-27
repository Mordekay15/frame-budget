// The simulated player. It picks spells from the labelled corpus (data/spells.json)
// and types them one character at a time, with the pauses people make, so the
// prefetch architecture has partial texts to work with.
//
// Skill changes how fast it types, how long it thinks, how good its spells are and
// how often it uses what the closest gloomling fears. Strong players also reuse a
// spell that worked, which is what makes a cache useful.

import { KINDS } from "../src/engine/game.js";
import { rng } from "../src/engine/rng.js";

export const SKILLS = {
  weak:    { cps: 4.0, think: [1500, 3500], smart: 0.2,  quality: { good: 0.2,  ok: 0.4, bad: 0.4 },  pause: 0.25, reuse: 0.1 },
  average: { cps: 6.0, think: [1000, 2500], smart: 0.5,  quality: { good: 0.45, ok: 0.4, bad: 0.15 }, pause: 0.15, reuse: 0.2 },
  strong:  { cps: 8.5, think: [600, 1500],  smart: 0.85, quality: { good: 0.75, ok: 0.2, bad: 0.05 }, pause: 0.08, reuse: 0.3 },
};

export class Bot {
  constructor(skill, seed, corpus) {
    this.s = SKILLS[skill];
    if (!this.s) throw new Error(`unknown skill ${skill}`);
    this.r = rng(seed);
    this.corpus = corpus;
    this.labels = new Map(corpus.map((c) => [c.text, c]));
    this.favourites = [];
    this.phase = "think";
    this.until = this.r.range(...this.s.think);
    this.text = "";
    this.typed = 0;
  }

  label(text) { return this.labels.get(text) || null; }

  /** Remember spells that hit what they aimed at twice as hard. */
  feedback(text, result) {
    if (result.hits.some((h) => h.mult > 1) && !this.favourites.includes(text)) this.favourites.push(text);
  }

  choose(game) {
    if (this.favourites.length && this.r() < this.s.reuse) return this.r.pick(this.favourites);
    let pool = this.corpus;
    if (this.r() < this.s.smart && game.enemies.length) {
      const near = game.nearest();
      if (near.x < 0.12 && game.shieldMs <= 0) pool = this.corpus.filter((c) => c.target === "shield");
      else {
        const weak = KINDS[near.kind].weak;
        const many = game.enemies.length >= 4;
        pool = this.corpus.filter((c) => weak.includes(c.element) && c.target !== "shield" && (many ? c.target === "all" : true));
      }
      if (!pool.length) pool = this.corpus;
    }
    // by quality, as this player's skill writes them
    const q = this.r();
    const want = q < this.s.quality.good ? "good" : q < this.s.quality.good + this.s.quality.ok ? "ok" : "bad";
    const byQ = pool.filter((c) => c.quality === want);
    return this.r.pick(byQ.length ? byQ : pool).text;
  }

  /** Called every tick. Returns what the player does now: typing and/or pressing Enter. */
  tick(now, game, busy) {
    const out = [];
    if (this.phase === "think" && now >= this.until) {
      this.text = this.choose(game);
      this.typed = 0;
      this.phase = "type";
      this.until = now;
    }
    while (this.phase === "type" && now >= this.until) {
      this.typed += 1;
      out.push({ type: "type", text: this.text.slice(0, this.typed) });
      let gap = this.r.range(0.6, 1.4) * (1000 / this.s.cps);
      if (this.text[this.typed - 1] === " " && this.r() < this.s.pause) gap += this.r.range(300, 900); // a pause between words
      if (this.typed >= this.text.length) { this.phase = "review"; gap = this.r.range(200, 700); }
      this.until += gap;
    }
    if (this.phase === "review" && now >= this.until && !busy) {
      out.push({ type: "submit", text: this.text });
      this.phase = "think";
      this.until = now + this.r.range(...this.s.think);
    }
    return out;
  }
}
