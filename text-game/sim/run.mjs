// The experiment runner.
//
//   node sim/run.mjs                                   one game, async at 200 ms, fake Jev
//   node sim/run.mjs --arch prefetch --deadline 250 --skill strong --games 10
//   node sim/run.mjs --sweep                           every architecture x deadline x skill, 30 games each
//   node sim/run.mjs --sweep --decider live --record data/recordings/live-1   real Jev, recorded
//   node sim/run.mjs --sweep --decider replay --replay data/recordings/live-1 the same run again, free
//
// Options:
//   --arch rules|blocking|async|cache|prefetch   --deadline ms     --skill weak|average|strong
//   --games N (or --reps N with --sweep)         --seed S          --coarse 0|1|2 (cache key)
//   --latency measured|synthetic|<csv glob>      (fake decider only; default: measured if Step 0 ran)
//   --shared-cache    one cache for all games in a cell, like one game server
//   --out DIR         default results/sim/<decider>-<time>
//
// Writes games.csv (one row per game), spells.csv (one row per spell) and summary.md.
// Games with the same index use the same seed in every cell (common random numbers),
// so differences between architectures are not differences in luck.

import path from "node:path";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { MODES } from "../src/engine/arch.js";
import { simulateGame } from "./simulate.mjs";
import { FakeDecider, LiveDecider, ReplayDecider, latencyModel, loadCorpus, writeCsv } from "./deciders.mjs";
import { SKILLS } from "./bot.mjs";
import { summaryMarkdown } from "./summary.mjs";

// In frames of the 33 ms tick: 1, 5, 6, 7 and 10. Picked from the Step 0 runs of 23 to 27 Oct
// (warm median 195 ms): from 0% of answers in time at one frame up to ~99% at ten frames,
// with the steps where the latency distribution changes fastest.
export const DEADLINES = [33, 167, 200, 233, 333];

function parseArgs(argv) {
  const o = { arch: "async", deadline: 200, skill: "average", games: 1, reps: 30, seed: 1, coarse: 1,
              decider: "fake", latency: "measured", sweep: false, sharedCache: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i], next = () => argv[++i];
    if (a === "--sweep") o.sweep = true;
    else if (a === "--shared-cache") o.sharedCache = true;
    else if (a === "--arch") o.arch = next();
    else if (a === "--deadline") o.deadline = +next();
    else if (a === "--skill") o.skill = next();
    else if (a === "--games") o.games = +next();
    else if (a === "--reps") o.reps = +next();
    else if (a === "--seed") o.seed = +next();
    else if (a === "--coarse") o.coarse = +next();
    else if (a === "--decider") o.decider = next();
    else if (a === "--latency") o.latency = next();
    else if (a === "--record") o.record = next();
    else if (a === "--replay") o.replay = next();
    else if (a === "--out") o.out = next();
    else if (a === "--quiet") o.quiet = true;
    else throw new Error(`unknown option ${a} (see the top of sim/run.mjs)`);
  }
  if (!MODES.includes(o.arch)) throw new Error(`--arch must be one of ${MODES.join(", ")}`);
  if (!SKILLS[o.skill]) throw new Error(`--skill must be one of ${Object.keys(SKILLS).join(", ")}`);
  return o;
}

/** The cells of the experiment: rules and blocking don't use the deadline, so they run once. */
export function cells(o) {
  if (!o.sweep) return [{ mode: o.arch, deadlineMs: o.deadline, skill: o.skill, n: o.games }];
  const out = [];
  for (const skill of Object.keys(SKILLS)) {
    for (const mode of MODES) {
      for (const deadlineMs of mode === "rules" || mode === "blocking" ? [null] : DEADLINES) {
        out.push({ mode, deadlineMs, skill, n: o.reps });
      }
    }
  }
  return out;
}

export async function run(o) {
  const corpus = loadCorpus();
  let decider;
  if (o.decider === "fake") decider = new FakeDecider({ corpus, latency: latencyModel(o.latency, o.seed), seed: o.seed });
  else if (o.decider === "live") decider = new LiveDecider({ recordDir: o.record ?? `data/recordings/live-${stamp()}` });
  else if (o.decider === "replay") {
    if (!o.replay) throw new Error("--decider replay needs --replay <recording dir>");
    decider = new ReplayDecider(o.replay);
  } else throw new Error("--decider must be fake, live or replay");

  const out = o.out ?? path.join("results", "sim", o.decider === "fake" ? "fake" : "", `${o.decider}-${stamp()}`);
  const games = [], spells = [];
  const plan = cells(o);
  const total = plan.reduce((s, c) => s + c.n, 0);
  let done = 0;
  for (const c of plan) {
    const cache = new Map();
    for (let g = 0; g < c.n; g++) {
      decider.reset?.();
      const { summary, events } = await simulateGame({
        mode: c.mode, deadlineMs: c.deadlineMs ?? 0, skill: c.skill, seed: o.seed * 100003 + g,
        decider, corpus, coarse: o.coarse, cache: o.sharedCache ? cache : new Map(),
      });
      games.push({ game: g, ...summary });
      spells.push(...events.map((e) => ({ game: g, ...e })));
      done += 1;
      if (!o.quiet && (done % 25 === 0 || done === total)) process.stdout.write(`\r${done}/${total} games`);
    }
  }
  if (!o.quiet) process.stdout.write("\n");
  decider.close();

  writeCsv(path.join(out, "games.csv"), games);
  writeCsv(path.join(out, "spells.csv"), spells);
  const meta = { decider: o.decider, latency: decider.latency?.describe?.() ?? o.decider, seed: o.seed,
                 coarse: o.coarse, sharedCache: o.sharedCache, games: games.length, created: new Date().toISOString(),
                 recording: o.decider === "live" ? decider.recordDir : o.replay ?? null };
  fs.writeFileSync(path.join(out, "meta.json"), JSON.stringify(meta, null, 2));
  fs.writeFileSync(path.join(out, "summary.md"), summaryMarkdown(games, meta));
  return { out, games, spells, meta };
}

function stamp() {
  return new Date().toISOString().replace(/[-:]/g, "").replace("T", "_").slice(0, 13);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const o = parseArgs(process.argv.slice(2));
    const { out } = await run(o);
    console.log(fs.readFileSync(path.join(out, "summary.md"), "utf8"));
    console.log(`Written to ${out}/`);
  } catch (err) {
    console.error(err.message);
    process.exit(1);
  }
}
