# Nuppu's Spell Valley: the spell-crafting test bench

The second test bench of the thesis, after the meeting with Joonas (22 Oct 2026). The decision under
study is no longer difficulty, which an if-statement can do, but **reading a spell the player
describes in their own words**:

> *"Make it remember the longest January night, when even the stars shivered"* → `frost / nearest / strong`

Jev answers three typed questions about the text in one request: the **element**, the **target** and
the **power** (vivid, original spells deserve more). A keyword parser is the fallback, and it can't
read that sentence at all: it finds no frost word. That gap is the reason to use a decision model here.

The architectures are the same as in the first (removed) wave-game bench: rules only, blocking, async with rules fallback,
cache, and prefetch. Prefetch gets a natural form here: **it asks Jev while the player is still
typing**, whenever they pause, so the answer is often back before Enter is pressed.

```
text-game/
  index.html, style.css     the web game
  src/engine/               the game and the decision layer, shared by the browser and the simulator
    spells.js               the three questions sent to Jev, and parsing the answer
    rules.js                the keyword fallback
    arch.js                 the five architectures
    game.js                 gloomlings, waves, damage (no drawing, no timing)
    signature.js            cache keys, with the coarseness knob
  src/browser/              drawing, input, and the channel to /api/decide
  api/decide.js             Vercel function: holds the API key and calls Jev
  lib/jev.mjs               the Jev client (Node standard library only)
  sim/                      the simulator, the bot, the Step 0 measurement
  data/spells.json          80 labelled spells the bot casts (a draft: please review the labels)
  test/                     node --test, all offline
```

Nothing to install: everything uses Node's standard library (Node 20 or newer).

## Play it locally

```bash
cd text-game
cp .env.example .env      # and put your TYPESAFE_API_KEY (or OPENROUTER_API_KEY) in it
npm run dev               # http://localhost:3000
```

Without a key the game still runs in **offline demo** mode: the keyword rules answer after a Jev-like
delay. The settings bar switches the architecture and the deadline; the meter in the corner shows frame
times, so the blocking architecture's freeze is visible as a red bar.

## Put it on Vercel

1. In Vercel, **Add New → Project**, import `frame-budget`.
2. **Root Directory:** `text-game`. Framework preset: **Other**. No build command.
3. **Environment Variables:** `TYPESAFE_API_KEY` (or `OPENROUTER_API_KEY`).
4. Deploy. The page is static; `/api/decide` is the only server code.

The key stays on the server. The route limits each visitor to 60 spells a minute, and a spell costs
about $0.00003, but a public link can still be shared, so consider Vercel's deployment protection.
Latency in the browser is Jev plus the trip to Vercel; **the thesis numbers come from the simulator**,
which calls Jev directly.

## Measure (Step 0 for this game)

The grading request is new (longer instructions, free text), so Jev's latency must be measured again
before choosing the deadlines. On your laptop, with the key in `.env`:

```bash
node sim/measure.mjs --warm 20 --cold 0 --same 3 --long 0 --inject 0   # a quick trial, ~30 requests
node sim/measure.mjs                                                     # the full run, ~570 requests, ~5 min
node sim/measure.mjs --analyze "results/step0/jev_spell_latency*.csv"    # pool all runs
```

As before, run it 3 or 4 times at different times of day, and commit the CSVs. Besides latency, the
summary (`results/step0/summary.md`) reports **format validity** (does every answer parse into the
schema), latency by spell length, **consistency** (three spells repeated 30 times), agreement with the
corpus labels against the keyword rules, and what Jev does with spells that try to give it orders.

## Simulate

```bash
npm run sim                                      # one game, async at 200 ms, fake Jev
node sim/run.mjs --arch prefetch --deadline 250 --skill strong --games 10
npm run sweep                                    # 3 skills x (rules, blocking, 3 archs x 5 deadlines) x 30 games
node sim/run.mjs --sweep --decider live --record data/recordings/live-1     # real Jev, recorded
node sim/run.mjs --sweep --decider replay --replay data/recordings/live-1   # the same run again, free
```

Each run writes `games.csv` (one row per game), `spells.csv` (one per spell) and `summary.md` to
`results/sim/...`. The **fake** decider (the default) uses real-shaped latency (this folder's Step 0 runs
once they exist, a lognormal fit until then) and made-up answers: it checks the pipeline and is never
thesis data. The simulated clock makes every run repeatable: the same seeds give the same games.

The bot types its spells one character at a time, with pauses between some words, and reuses spells
that worked, so prefetch and the cache are tested the way a player would use them.

## Tests

```bash
npm test
```
