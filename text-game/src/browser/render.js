// Storybook drawing on a canvas: soft pastel watercolour fills, inky outlines,
// a quiet northern valley. Everything is drawn in code, so there are no image files.
// The hero is an original character, Nuppu ("bud" in Finnish): a small round white
// valley creature in a red scarf.

import { KINDS } from "../engine/game.js";

export const W = 960, H = 540;
const INK = "#3b3a4a";
const HOME_X = 150, FIELD_END = 930;
export const ELEMENT_COLORS = {
  frost: "#a9dcf3", fire: "#f2905e", wind: "#d5eedc", water: "#6fa6dc",
  light: "#ffe28a", earth: "#b48e68", nature: "#8cc084", fizzle: "#c9c6cf",
};

const fieldX = (x) => HOME_X + x * (FIELD_END - HOME_X);
const laneY = (lane) => 360 + lane * 110;

// Tiny deterministic noise for the hand-drawn wobble.
function wob(i, amp = 1.5) {
  const s = Math.sin(i * 12.9898) * 43758.5453;
  return (s - Math.floor(s) - 0.5) * 2 * amp;
}

function blob(ctx, cx, cy, rx, ry, seed = 0, points = 18, amp = 1.6) {
  ctx.beginPath();
  for (let i = 0; i <= points; i++) {
    const a = (i / points) * Math.PI * 2;
    const r = 1 + wob(seed + i, amp) / Math.max(rx, ry);
    const x = cx + Math.cos(a) * rx * r, y = cy + Math.sin(a) * ry * r;
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  }
  ctx.closePath();
}

function ink(ctx, fill, width = 2.4) {
  if (fill) { ctx.fillStyle = fill; ctx.fill(); }
  ctx.lineWidth = width;
  ctx.strokeStyle = INK;
  ctx.lineJoin = ctx.lineCap = "round";
  ctx.stroke();
}

function drawBackground() {
  const c = document.createElement("canvas");
  c.width = W; c.height = H;
  const ctx = c.getContext("2d");
  const sky = ctx.createLinearGradient(0, 0, 0, 330);
  sky.addColorStop(0, "#cfe3ee");
  sky.addColorStop(0.7, "#f6e6d6");
  sky.addColorStop(1, "#f9eedf");
  ctx.fillStyle = sky;
  ctx.fillRect(0, 0, W, H);

  // a pale sun and soft clouds
  ctx.globalAlpha = 0.8;
  blob(ctx, 640, 92, 40, 40, 3, 24, 1); ink(ctx, "#fff3c4", 1.6);
  ctx.globalAlpha = 0.9;
  for (const [x, y, s] of [[230, 70, 1], [520, 110, 0.8], [880, 60, 0.7]]) {
    for (let k = 0; k < 4; k++) { blob(ctx, x + k * 26 * s, y - (k % 2) * 10 * s, 26 * s, 18 * s, x + k, 14, 1.2); ctx.fillStyle = "#fffaf3"; ctx.fill(); }
  }
  ctx.globalAlpha = 1;

  // far hills, near hills
  const hill = (base, amp, color, seed) => {
    ctx.beginPath();
    ctx.moveTo(0, H);
    for (let x = 0; x <= W; x += 16) ctx.lineTo(x, base + Math.sin(x / 140 + seed) * amp + wob(x + seed, 2));
    ctx.lineTo(W, H);
    ctx.closePath();
    ink(ctx, color, 2);
  };
  hill(250, 26, "#c3d9c9", 1);
  // pines on the far hill
  for (let i = 0; i < 26; i++) {
    const x = 20 + i * 37 + wob(i, 10), y = 258 + Math.sin(x / 140 + 1) * 26;
    const h = 38 + wob(i + 7, 10);
    ctx.beginPath(); ctx.moveTo(x, y - h); ctx.lineTo(x - 11, y); ctx.lineTo(x + 11, y); ctx.closePath();
    ink(ctx, i % 3 ? "#7fa592" : "#6e9783", 1.6);
  }
  hill(320, 14, "#d9e8c8", 4);

  // the meadow the gloomlings cross
  const ground = ctx.createLinearGradient(0, 330, 0, H);
  ground.addColorStop(0, "#dcebc3");
  ground.addColorStop(1, "#c8dfae");
  ctx.fillStyle = ground;
  ctx.fillRect(0, 336, W, H - 336);
  ctx.globalAlpha = 0.35;
  for (let i = 0; i < 140; i++) {
    const x = (i * 97) % W, y = 350 + ((i * 53) % 180);
    ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + 3, y - 7); ctx.moveTo(x + 4, y); ctx.lineTo(x + 8, y - 5);
    ctx.strokeStyle = "#7f9f6a"; ctx.lineWidth = 1.3; ctx.stroke();
  }
  ctx.globalAlpha = 1;
  // a few flowers
  for (let i = 0; i < 24; i++) {
    const x = 180 + ((i * 131) % 760), y = 360 + ((i * 71) % 170);
    blob(ctx, x, y, 3.2, 3.2, i, 8, 0.4); ctx.fillStyle = ["#f7c6d0", "#fff1a8", "#cfe0ff"][i % 3]; ctx.fill();
  }

  // the cottage: cream walls, a turf roof, a round window, a chimney
  ctx.beginPath(); ctx.rect(18, 300, 104, 92); ink(ctx, "#f4e7cf");
  ctx.beginPath(); ctx.moveTo(6, 306); ctx.quadraticCurveTo(70, 238, 134, 306); ctx.closePath(); ink(ctx, "#8db27a");
  ctx.beginPath(); ctx.rect(92, 248, 16, 34); ink(ctx, "#c98f73");
  blob(ctx, 50, 336, 13, 13, 9, 16, 0.6); ink(ctx, "#fff6c9", 2);
  ctx.beginPath(); ctx.moveTo(37, 336); ctx.lineTo(63, 336); ctx.moveTo(50, 323); ctx.lineTo(50, 349); ctx.lineWidth = 1.6; ctx.stroke();
  ctx.beginPath(); ctx.roundRect(78, 340, 26, 52, [13, 13, 0, 0]); ink(ctx, "#9fb6d8");

  // paper grain over everything
  const img = ctx.getImageData(0, 0, W, H);
  for (let i = 0; i < img.data.length; i += 4) {
    const n = (wob(i, 1) + wob(i * 1.7, 1)) * 5;
    img.data[i] += n; img.data[i + 1] += n; img.data[i + 2] += n;
  }
  ctx.putImageData(img, 0, 0);
  return c;
}

export class Renderer {
  constructor(canvas) {
    this.ctx = canvas.getContext("2d");
    this.bg = drawBackground();
    this.anims = [];     // spell projectiles and bursts
    this.floats = [];    // floating texts
    this.seenEffects = 0;
    this.frameGaps = [];
  }

  noteFrame(gapMs) {
    this.frameGaps.push(gapMs);
    if (this.frameGaps.length > 90) this.frameGaps.shift();
  }

  /** A spell was cast: queue its projectiles and texts. */
  spell(result, t) {
    const color = ELEMENT_COLORS[result.element];
    if (result.target === "shield" && result.element !== "fizzle") {
      this.anims.push({ type: "shieldPop", t0: t, color });
      return;
    }
    if (!result.hits.length || result.element === "fizzle") {
      this.anims.push({ type: "fizzle", t0: t });
      this.floats.push({ text: "fizzle…", x: 150, y: 330, t0: t, color: "#7d7891" });
    }
    for (const h of result.hits) {
      const x = fieldX(h.x), y = laneY(h.lane) - 20;
      this.anims.push({ type: "bolt", t0: t, x, y, color, element: result.element, power: result.power });
      if (h.mult !== 1) this.floats.push({ text: h.mult > 1 ? "×2!" : "×½", x, y: y - 40, t0: t + 300, color: h.mult > 1 ? "#d0573a" : "#6b7a99" });
    }
  }

  reset() {
    this.anims = [];
    this.floats = [];
    this.seenEffects = 0;
  }

  draw(game, layer, now, hero) {
    const ctx = this.ctx;
    ctx.drawImage(this.bg, 0, 0);
    for (; this.seenEffects < game.effects.length; this.seenEffects++) {
      const fx = game.effects[this.seenEffects];
      if (fx.type === "hurt") this.floats.push({ text: "ouch!", x: 70, y: 280, t0: now, color: "#d0573a" });
      if (fx.type === "blocked") this.floats.push({ text: "blocked!", x: 70, y: 280, t0: now, color: "#5f8fc4" });
    }

    // chimney smoke
    for (let i = 0; i < 4; i++) {
      const p = ((now / 2600 + i / 4) % 1);
      ctx.globalAlpha = 0.5 * (1 - p);
      blob(ctx, 100 + Math.sin(p * 5 + i) * 8, 244 - p * 70, 7 + p * 10, 6 + p * 8, i, 10, 0.6);
      ctx.fillStyle = "#ffffff"; ctx.fill();
    }
    ctx.globalAlpha = 1;

    // shield around the cottage
    if (game.shieldMs > 0) {
      ctx.globalAlpha = 0.25 + 0.1 * Math.sin(now / 200);
      blob(ctx, 80, 340, 105, 95, Math.floor(now / 300), 22, 2.5);
      ctx.fillStyle = "#cfe8ff"; ctx.fill();
      ctx.globalAlpha = 0.7; ctx.lineWidth = 2; ctx.strokeStyle = "#7aa7d6"; ctx.stroke();
      ctx.globalAlpha = 1;
    }

    // gloomlings, far ones first
    for (const e of [...game.enemies].sort((a, b) => a.lane - b.lane)) this.gloomling(e, now);

    this.hero(now, layer?.busy, hero);
    this.animations(now);
    this.hud(game);
    this.frameMeter();
  }

  gloomling(e, now) {
    const ctx = this.ctx, k = KINDS[e.kind];
    const x = fieldX(e.x), y = laneY(e.lane) + Math.sin(now / 300 + e.id) * 3;
    const r = 18 + (k.hp / 60) * 8;
    ctx.globalAlpha = 0.18;
    blob(ctx, x, y + r * 0.9, r * 0.9, 5, e.id, 12, 0.5); ctx.fillStyle = INK; ctx.fill();
    ctx.globalAlpha = 1;
    // a ghostly body with a wavy hem
    ctx.beginPath();
    ctx.moveTo(x - r, y);
    ctx.arc(x, y - r * 0.2, r, Math.PI, 0);
    for (let i = 0; i <= 6; i++) ctx.lineTo(x + r - (i * 2 * r) / 6, y + r * 0.55 + (i % 2 ? -5 : 4) + Math.sin(now / 160 + i) * 1.5);
    ctx.closePath();
    ink(ctx, k.color, 2.2);
    // eyes
    for (const dx of [-0.35, 0.3]) {
      blob(ctx, x + dx * r, y - r * 0.3, 5, 6, e.id + dx * 10, 10, 0.3); ink(ctx, "#fffdf6", 1.5);
      ctx.beginPath(); ctx.arc(x + dx * r - 1.5, y - r * 0.27, 2.2, 0, 7); ctx.fillStyle = INK; ctx.fill();
    }
    // health
    const f = Math.max(0, e.hp / e.maxHp);
    ctx.fillStyle = "#ffffffaa"; ctx.fillRect(x - 16, y - r - 16, 32, 5);
    ctx.fillStyle = "#d77a6b"; ctx.fillRect(x - 16, y - r - 16, 32 * f, 5);
    ctx.font = "13px 'Patrick Hand', cursive"; ctx.fillStyle = INK; ctx.textAlign = "center";
    ctx.fillText(e.kind, x, y + r + 18);
  }

  hero(now, charging, name) {
    const ctx = this.ctx;
    const x = 152, y = 410 + Math.sin(now / 420) * 2.5;
    ctx.globalAlpha = 0.2; blob(ctx, x, y + 34, 26, 6, 1, 12, 0.4); ctx.fillStyle = INK; ctx.fill(); ctx.globalAlpha = 1;
    // feet, body, ears
    for (const dx of [-11, 11]) { blob(ctx, x + dx, y + 30, 9, 6, dx, 10, 0.4); ink(ctx, "#fbfaf6", 2); }
    blob(ctx, x, y, 30, 34, 2, 22, 1); ink(ctx, "#fbfaf6", 2.6);
    for (const dx of [-15, 15]) { blob(ctx, x + dx, y - 33, 7, 8, dx + 4, 10, 0.5); ink(ctx, "#fbfaf6", 2.2); }
    // face
    for (const dx of [-10, 9]) {
      ctx.beginPath(); ctx.ellipse(x + dx, y - 10, 4.2, 5.4, 0, 0, 7); ctx.fillStyle = INK; ctx.fill();
      ctx.beginPath(); ctx.arc(x + dx + 1.4, y - 12, 1.4, 0, 7); ctx.fillStyle = "#fff"; ctx.fill();
    }
    ctx.globalAlpha = 0.5;
    for (const dx of [-18, 17]) { ctx.beginPath(); ctx.ellipse(x + dx, y + 1, 5, 3, 0, 0, 7); ctx.fillStyle = "#f4a7b0"; ctx.fill(); }
    ctx.globalAlpha = 1;
    ctx.beginPath(); ctx.arc(x, y - 2, 4, 0.2, Math.PI - 0.2); ctx.lineWidth = 1.8; ctx.strokeStyle = INK; ctx.stroke();
    // the red scarf
    ctx.beginPath(); ctx.moveTo(x - 27, y + 8); ctx.quadraticCurveTo(x, y + 20, x + 27, y + 8);
    ctx.lineTo(x + 26, y + 16); ctx.quadraticCurveTo(x, y + 28, x - 26, y + 16); ctx.closePath(); ink(ctx, "#d9584d", 2);
    ctx.beginPath(); ctx.moveTo(x + 14, y + 18); ctx.lineTo(x + 24, y + 36); ctx.lineTo(x + 31, y + 32); ctx.lineTo(x + 21, y + 16); ink(ctx, "#d9584d", 2);
    // wand
    ctx.beginPath(); ctx.moveTo(x + 24, y - 2); ctx.lineTo(x + 46, y - 24); ctx.lineWidth = 3; ctx.strokeStyle = "#8a6a4f"; ctx.stroke();
    const glow = charging ? 7 + Math.sin(now / 60) * 3 : 3.5;
    ctx.globalAlpha = charging ? 0.9 : 0.6;
    blob(ctx, x + 47, y - 26, glow, glow, Math.floor(now / 90), 10, charging ? 1.4 : 0.3);
    ctx.fillStyle = "#fff1a6"; ctx.fill();
    ctx.globalAlpha = 1;
    if (charging) {
      for (let i = 0; i < 5; i++) {
        const a = now / 250 + i * 1.3, rr = 16 + Math.sin(now / 130 + i) * 5;
        ctx.beginPath(); ctx.arc(x + 47 + Math.cos(a) * rr, y - 26 + Math.sin(a) * rr, 1.8, 0, 7); ctx.fillStyle = "#f5c95b"; ctx.fill();
      }
    }
    ctx.font = "15px 'Patrick Hand', cursive"; ctx.fillStyle = INK; ctx.textAlign = "center";
    ctx.fillText(name, x, y + 54);
  }

  animations(now) {
    const ctx = this.ctx;
    const from = { x: 199, y: 384 };
    this.anims = this.anims.filter((a) => now - a.t0 < 900);
    for (const a of this.anims) {
      const p = (now - a.t0) / 900;
      if (a.type === "bolt") {
        const fly = Math.min(1, p / 0.4);
        const x = from.x + (a.x - from.x) * fly, y = from.y + (a.y - from.y) * fly - Math.sin(fly * Math.PI) * 60;
        const size = { weak: 6, medium: 9, strong: 12, mighty: 16 }[a.power] || 8;
        if (fly < 1) { blob(ctx, x, y, size, size, Math.floor(now / 50), 10, 1.5); ink(ctx, a.color, 1.8); }
        else {
          const q = (p - 0.4) / 0.6;
          ctx.globalAlpha = 1 - q;
          for (let i = 0; i < 10; i++) {
            const ang = i * 0.63 + a.x, d = q * (30 + size * 2);
            blob(ctx, a.x + Math.cos(ang) * d, a.y + Math.sin(ang) * d, size * 0.45, size * 0.45, i, 8, 0.8);
            ctx.fillStyle = a.color; ctx.fill();
          }
          ctx.globalAlpha = 1;
        }
      } else if (a.type === "shieldPop") {
        ctx.globalAlpha = 1 - p;
        blob(ctx, 80, 340, 60 + p * 60, 50 + p * 55, 5, 22, 2); ctx.lineWidth = 3; ctx.strokeStyle = a.color; ctx.stroke();
        ctx.globalAlpha = 1;
      } else if (a.type === "fizzle") {
        ctx.globalAlpha = 1 - p;
        for (let i = 0; i < 4; i++) { blob(ctx, from.x + i * 6, from.y - p * 40 - i * 5, 5, 5, i, 8, 1); ctx.fillStyle = "#c9c6cf"; ctx.fill(); }
        ctx.globalAlpha = 1;
      }
    }
    this.floats = this.floats.filter((f) => now - f.t0 < 1100);
    for (const f of this.floats) {
      const p = (now - f.t0) / 1100;
      if (p < 0) continue;
      ctx.globalAlpha = 1 - p;
      ctx.font = "22px 'Patrick Hand', cursive"; ctx.fillStyle = f.color; ctx.textAlign = "center";
      ctx.fillText(f.text, f.x, f.y - p * 30);
      ctx.globalAlpha = 1;
    }
  }

  hud(game) {
    const ctx = this.ctx;
    for (let i = 0; i < 5; i++) {
      const x = 26 + i * 30, y = 30, full = i < game.hearts;
      ctx.beginPath();
      ctx.moveTo(x, y + 6);
      ctx.bezierCurveTo(x - 13, y - 4, x - 6, y - 15, x, y - 6);
      ctx.bezierCurveTo(x + 6, y - 15, x + 13, y - 4, x, y + 6);
      ink(ctx, full ? "#e46f6f" : "#efe4e0", 2);
    }
    ctx.font = "22px 'Patrick Hand', cursive"; ctx.fillStyle = INK; ctx.textAlign = "left";
    ctx.fillText(`Wave ${Math.max(1, game.wave)} of ${game.maxWaves}`, 186, 38);
    ctx.fillText(`Gloomlings sent home: ${game.kills}`, 330, 38);
  }

  /** The last 3 seconds of frame times. Blocking shows up as a tall red bar. */
  frameMeter() {
    const ctx = this.ctx, x0 = 760, y0 = 20, w = 180, h = 40;
    ctx.fillStyle = "#ffffffaa"; ctx.fillRect(x0, y0, w, h);
    const budget = 1000 / 30;
    const scale = h / (budget * 4);
    this.frameGaps.forEach((g, i) => {
      const bh = Math.min(h, g * scale);
      ctx.fillStyle = g > budget * 1.5 ? "#d9584d" : "#8cb39a";
      ctx.fillRect(x0 + i * 2, y0 + h - bh, 1.6, bh);
    });
    ctx.strokeStyle = INK; ctx.lineWidth = 1; ctx.setLineDash([3, 3]);
    ctx.beginPath(); ctx.moveTo(x0, y0 + h - budget * scale); ctx.lineTo(x0 + w, y0 + h - budget * scale); ctx.stroke();
    ctx.setLineDash([]);
    const worst = Math.max(...this.frameGaps, 0);
    ctx.font = "13px 'Patrick Hand', cursive"; ctx.fillStyle = INK;
    ctx.textAlign = "left";
    ctx.fillText("frame time", x0, y0 + h + 14);
    ctx.textAlign = "right";
    ctx.fillText(`worst ${worst.toFixed(0)} ms, budget 33`, x0 + w, y0 + h + 14);
  }
}
