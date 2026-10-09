# Step 2: the game

**Question:** is there a game in which difficulty adjustment can matter, and can
we reproduce "too hard", "about right" and "too easy" on demand?

## What was built

| File | What it does |
|---|---|
| `framebudget/game.py` | The game: health, waves, damage, the bot, and the experience metrics. |
| `framebudget/sim.py` | `run_episode`: plays one game on the loop from Step 1 with an *architecture* in charge of difficulty. `EpisodeResult.row()` is one row of the final dataset. |
| `scripts/step2_fixed_difficulty.py` | 200 games per skill at fixed difficulty, summary and plot. |

## The rules of the game

- The player starts with 100 health. A game is 30 waves, or ends early if the player dies.
- A wave has `count` enemies. Each living enemy deals `2 * mult` damage per second.
- The bot kills one enemy at a time. The time to the next kill is drawn from an
  exponential distribution with mean `1 / skill`, so kills come in random
  streaks, like a real player. Each wave the skill also wobbles by about 15%
  (good waves and bad waves).
- After clearing a wave, the player regains 15 health, there is a 1 s pause, and the next wave spawns.
- **The decision under study** is made at the moment a wave is cleared: `count`
  (3, 5, 8 or 12) and `mult` (0.75, 1.0, 1.25 or 1.5) of the next wave. It has
  to be in place by the time the pause ends.

Damage per wave grows roughly with `count²`: while the bot works through *n*
enemies, *n* are alive, then *n-1*, and so on. So `count` is the coarse lever and
`mult` the fine one.

## Skills and how "bored" and "too hard" are measured

| bot | kills per second |
|---|---|
| weak | 1.2 |
| medium | 2.0 |
| strong | 3.5 |

These were calibrated so that at the default difficulty (5 enemies, x1.0) the
three scenarios appear. Every tick the player's health is recorded, and a game is described by:

- **bored**: share of time with health at or above 90% (nothing threatens the player),
- **danger**: share of time at or below 20%,
- **in band**: the rest, where we want the player to be,
- and of course **death rate** and waves survived.

Defining these before building any adjustment is what makes Step 3's "measurable
shift" measurable.

## Determinism

The game gets all its randomness from one `random.Random(seed)`, and it runs on
the `SimClock` from Step 1. The same seed gives exactly the same game (there is a
test for it). 600 games take about 5 seconds.

## Run it

```bash
python -m scripts.step2_fixed_difficulty
```

## Done when

The weak bot dies, the strong bot is bored: see `results/step2/summary.md` and
`health_traces.png`.
