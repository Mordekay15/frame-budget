// The game itself, with no drawing and no timing of its own: `update(dtMs)` moves
// it forward, `cast(decision)` applies a spell. The browser calls update() from a
// fixed 33 ms tick; the simulator calls it from a simulated clock. Same rules both ways.
//
// Gloomlings drift from the right edge (x = 1) to the hero's home (x = 0). Each kind
// is weak against two elements (double damage) and resists one (half damage), so the
// element Jev reads from the text decides whether a spell works.

import { rng } from "./rng.js";

export const TICK_MS = 1000 / 30;

export const KINDS = {
  ember:   { hp: 40, speed: 1.15, weak: ["frost", "water"], resist: "fire",   color: "#e8916b" },
  icicle:  { hp: 40, speed: 1.0,  weak: ["fire", "light"],  resist: "frost",  color: "#9cc7e4" },
  fog:     { hp: 30, speed: 1.3,  weak: ["wind", "light"],  resist: "water",  color: "#b9b3c9" },
  pebble:  { hp: 60, speed: 0.75, weak: ["water", "nature"], resist: "earth", color: "#a99c8a" },
  bramble: { hp: 45, speed: 0.9,  weak: ["fire", "wind"],   resist: "nature", color: "#8fae7e" },
};
export const DAMAGE = { weak: 15, medium: 28, strong: 42, mighty: 60 };
export const SHIELD_MS = { weak: 4000, medium: 6000, strong: 9000, mighty: 13000 };
const FIZZLE_DAMAGE = 4;
const BASE_SPEED = 1 / 60; // field widths per second: a crossing takes about a minute
const SPAWN_GAP_MS = 7000;
const WAVE_BREAK_MS = 4000;

export class Game {
  constructor({ seed = 1, waves = 8, hearts = 5 } = {}) {
    this.r = rng(seed);
    this.maxWaves = waves;
    this.hearts = hearts;
    this.timeMs = 0;
    this.wave = 0;
    this.enemies = [];
    this.toSpawn = [];
    this.spawnInMs = WAVE_BREAK_MS;
    this.shieldMs = 0;
    this.nextId = 1;
    this.over = false;
    this.won = false;
    this.kills = 0;
    this.effects = []; // what happened, for drawing; the simulator ignores it
  }

  startWave() {
    this.wave += 1;
    const kinds = Object.keys(KINDS);
    const n = 2 + this.wave;
    this.toSpawn = Array.from({ length: n }, () => kinds[this.r.int(kinds.length)]);
    this.spawnInMs = 0;
  }

  update(dtMs) {
    if (this.over) return;
    this.timeMs += dtMs;
    this.shieldMs = Math.max(0, this.shieldMs - dtMs);
    this.spawnInMs -= dtMs;
    if (this.spawnInMs <= 0) {
      if (this.toSpawn.length) {
        const kind = this.toSpawn.shift();
        const k = KINDS[kind];
        const hp = k.hp * (1 + 0.08 * (this.wave - 1));
        this.enemies.push({ id: this.nextId++, kind, x: 1.02, lane: this.r.range(0, 1), hp, maxHp: hp,
                            speed: BASE_SPEED * k.speed * (1 + 0.04 * (this.wave - 1)) });
        this.spawnInMs = SPAWN_GAP_MS * this.r.range(0.7, 1.3);
      } else if (!this.enemies.length) {
        if (this.wave >= this.maxWaves) { this.over = this.won = true; return; }
        this.startWave();
        this.spawnInMs = this.wave === 1 ? 0 : WAVE_BREAK_MS;
      }
    }
    for (const e of this.enemies) e.x -= e.speed * dtMs / 1000;
    for (const e of this.enemies.filter((e) => e.x <= 0)) {
      if (this.shieldMs > 0) this.effects.push({ type: "blocked", id: e.id, at: this.timeMs });
      else { this.hearts -= 1; this.effects.push({ type: "hurt", at: this.timeMs }); }
      e.hp = 0;
    }
    this.enemies = this.enemies.filter((e) => e.hp > 0);
    if (this.hearts <= 0) { this.hearts = 0; this.over = true; }
  }

  nearest() {
    return this.enemies.reduce((a, e) => (!a || e.x < a.x ? e : a), null);
  }

  /** Apply a spell. Returns what it did, for the log and the drawing. */
  cast(d) {
    const out = { ...d, hits: [], at: this.timeMs };
    if (d.target === "shield" && d.element !== "fizzle") {
      this.shieldMs = Math.max(this.shieldMs, SHIELD_MS[d.power]);
      this.effects.push({ type: "shield", ...out });
      return out;
    }
    let targets = [];
    if (d.target === "all") targets = this.enemies;
    else if (d.target === "strongest") targets = this.enemies.length ? [this.enemies.reduce((a, e) => (e.hp > a.hp ? e : a))] : [];
    else targets = this.nearest() ? [this.nearest()] : [];
    const base = d.element === "fizzle" ? FIZZLE_DAMAGE : DAMAGE[d.power] * (d.target === "all" ? 0.5 : 1);
    for (const e of targets) {
      const k = KINDS[e.kind];
      const mult = k.weak.includes(d.element) ? 2 : k.resist === d.element ? 0.5 : 1;
      e.hp -= base * mult;
      out.hits.push({ id: e.id, x: e.x, lane: e.lane, mult, killed: e.hp <= 0 });
      if (e.hp <= 0) this.kills += 1;
    }
    this.enemies = this.enemies.filter((e) => e.hp > 0);
    this.effects.push({ type: "spell", ...out });
    return out;
  }
}
