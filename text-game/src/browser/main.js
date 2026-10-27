// The browser game: a fixed 33 ms tick (30 fps) driven by requestAnimationFrame,
// the decision layer in between the text box and the game.

import { Game, KINDS, TICK_MS } from "../engine/game.js";
import { DecisionLayer } from "../engine/arch.js";
import { FetchChannel, OfflineChannel } from "./channel.js";
import { Renderer, ELEMENT_COLORS } from "./render.js";

const HERO = "Nuppu";
const $ = (id) => document.getElementById(id);
const canvas = $("game"), input = $("spell"), renderer = new Renderer(canvas);

const SOURCE_TEXT = {
  jev: (ev) => `Jev, in ${Math.round(ev.waitMs)} ms`,
  rules: (ev) => ev.failed ? "rules (Jev failed)" : ev.requested ? `rules (Jev too slow, ${Math.round(ev.waitMs)} ms)` : "rules",
  cache: () => "cache, instant",
  prefetch: (ev) => `prefetch, ${Math.round(ev.waitMs)} ms`,
};

let game, layer, running = false, lastFrame = 0, acc = 0, serverOk = false;

async function detectServer() {
  try {
    const r = await fetch("/api/decide");
    const b = await r.json();
    serverOk = !!(b.ok && b.provider);
  } catch { serverOk = false; }
  const sel = $("source");
  sel.querySelector('[value="server"]').disabled = !serverOk;
  if (!serverOk) {
    sel.value = "offline";
    $("server-note").textContent = "No Jev key on the server, so the offline demo answers (keyword rules + Jev-like delay).";
  }
}

function start() {
  const mode = $("arch").value, deadlineMs = +$("deadline").value;
  const channel = $("source").value === "server" ? new FetchChannel() : new OfflineChannel(Date.now() % 1000);
  game = new Game({ seed: Math.floor(Math.random() * 1e9) });
  layer = new DecisionLayer({
    mode, channel, deadlineMs,
    onCast: (decision, ev) => {
      const result = game.cast(decision);
      renderer.spell(result, performance.now());
      showLast(ev);
      showStats();
    },
  });
  renderer.reset();
  $("overlay").hidden = true;
  $("last").innerHTML = "<p class='muted'>Your spells will appear here.</p>";
  showStats();
  running = true;
  acc = 0;
  lastFrame = performance.now();
  input.disabled = false;
  input.focus();
}

function frame(now) {
  const gap = now - lastFrame;
  lastFrame = now;
  renderer.noteFrame(gap);
  if (running) {
    acc += Math.min(gap, 3000);
    while (acc >= TICK_MS) {
      game.update(TICK_MS);
      layer.onTick(performance.now());
      acc -= TICK_MS;
    }
    if (game.over) end();
  }
  if (game) renderer.draw(game, layer, now, HERO);
  requestAnimationFrame(frame);
}

function end() {
  running = false;
  input.disabled = true;
  const evs = layer.events.filter((e) => e.source);
  const fromJev = evs.filter((e) => e.source !== "rules").length;
  $("overlay-title").textContent = game.won ? "The valley is safe!" : "The gloom got in…";
  $("overlay-text").innerHTML =
    `${game.kills} gloomlings sent home in ${game.wave} waves.<br>` +
    `${evs.length} spells, ${fromJev} decided by the model (${evs.length ? Math.round((100 * fromJev) / evs.length) : 0}%).`;
  $("start-btn").textContent = "Play again";
  $("overlay").hidden = false;
}

function cast() {
  if (!running) return;
  const text = input.value;
  const ok = layer.onSubmit(text, performance.now());
  if (ok) input.value = "";
  else { input.classList.remove("shake"); void input.offsetWidth; input.classList.add("shake"); }
}

function chip(label, color) {
  return `<span class="chip" style="background:${color}">${label}</span>`;
}

function showLast(ev) {
  const d = ev.decision;
  const same = d.element === ev.rules.element && d.target === ev.rules.target && d.power === ev.rules.power;
  $("last").innerHTML = `
    <p class="said">“${escapeHtml(ev.text)}”</p>
    <p>${chip(d.element, ELEMENT_COLORS[d.element])} ${chip(d.target, "#efe6d6")} ${chip(d.power, "#f3dfe6")}</p>
    <p class="muted">Decided by <b>${SOURCE_TEXT[ev.source](ev)}</b>${ev.freezeMs ? `, the game froze for ${Math.round(ev.freezeMs)} ms` : ""}.
    ${ev.source === "rules" ? "" : same ? "The keyword rules would have said the same." :
      `The keyword rules would have said ${ev.rules.element} / ${ev.rules.target} / ${ev.rules.power}.`}</p>`;
}

function showStats() {
  const evs = layer.events.filter((e) => e.source);
  const n = evs.length, waits = evs.map((e) => e.waitMs);
  const byModel = evs.filter((e) => e.source !== "rules").length;
  const c = layer.counts;
  $("stats").innerHTML = `
    <tr><td>Spells cast</td><td>${n}</td></tr>
    <tr><td>Decided by the model</td><td>${n ? Math.round((100 * byModel) / n) : 0}%</td></tr>
    <tr><td>Average wait</td><td>${n ? Math.round(waits.reduce((a, b) => a + b, 0) / n) : 0} ms</td></tr>
    <tr><td>Requests to Jev</td><td>${c.requests + c.prefetchRequests}${c.prefetchRequests ? ` (${c.prefetchRequests} prefetch)` : ""}</td></tr>
    <tr><td>Answers too late</td><td>${c.late}</td></tr>`;
}

function escapeHtml(s) {
  return s.replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[ch]);
}

function fieldGuide() {
  $("guide").innerHTML = Object.entries(KINDS).map(([name, k]) =>
    `<li><span class="dot" style="background:${k.color}"></span><b>${name}</b>
     fears ${k.weak.join(" and ")}, shrugs off ${k.resist}</li>`).join("");
}

input.addEventListener("input", () => layer?.onTyping(input.value, performance.now()));
input.addEventListener("keydown", (e) => { if (e.key === "Enter") cast(); });
$("cast-btn").addEventListener("click", cast);
$("start-btn").addEventListener("click", start);
$("arch").addEventListener("change", () => {
  $("arch-help").textContent = $("arch").selectedOptions[0].dataset.help;
});
$("arch").dispatchEvent(new Event("change"));

fieldGuide();
detectServer();
game = new Game();
requestAnimationFrame(frame);
