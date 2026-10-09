# Step 3: the rule-based baseline

**Question:** does difficulty adjustment change anything in this game? If a
well-known policy from the literature cannot move the outcomes, nothing
Jev does could be measured either.

## What was built

| File | What it does |
|---|---|
| `framebudget/rules.py` | `HunickePolicy`: the comfort-zone policy, and `LADDER`: the 16 difficulties ordered from easiest to hardest. |
| `framebudget/arch.py` | `RulesOnly`: the architecture where the policy decides every wave. More architectures are added here in later steps. |
| `scripts/step3_rules_baseline.py` | Fixed vs rules, 200 games per skill, same seeds. |

## How the policy works

Based on Hunicke and Chapman (2004), *AI for Dynamic Difficulty Adjustment in
Games*, and Hunicke (2005), *The case for dynamic difficulty adjustment in games*.
Their Hamlet system modelled the damage a player takes as a normal
distribution, estimated the probability of death from it, and intervened when that
probability crossed a threshold. Please check the exact threshold and wording
against the paper before you cite it; the 40% here comes from your plan.

At every decision point:

1. **Kill rate.** The average of `count / clear time` over the last 5 waves.
2. **Expected damage of a wave** at a candidate difficulty:
   `2 * mult * n(n+1)/2 / kill_rate`, corrected by how far real waves have
   deviated from this formula so far (the mean ratio of actual to expected damage).
3. **Spread.** The standard deviation of that ratio (at least 25%).
4. **P(death)** over a horizon of 4 waves: the total damage of 4 waves minus 3
   regenerations, as a normal distribution, compared with current health.
5. **Intervene down.** If P(death) at the current difficulty is above 40%, step
   down the ladder until it is not.
6. **Intervene up.** If the player is bored (health at least 90%) and one step up
   would still keep P(death) under 10%, step up one level. This is our
   symmetric extension. Hamlet mainly helped struggling players, but we need the
   strong bot to be affected too.

### Two things that went wrong while tuning, worth a sentence in the thesis

- With a one-wave horizon the policy happily raised the difficulty for everyone,
  because a single wave almost never kills a healthy player. Health then eroded
  over several waves, and the policy noticed too late. **A longer horizon** (4
  waves) fixed that.
- Raising difficulty whenever P(death) was low drove even the weak bot into
  harder waves at the start of each game. Making the upward step depend on the
  **bored** condition fixed that.

## Results (200 games per cell, `results/step3/summary.md`)

| skill | death rate fixed → rules | bored fixed → rules | in band fixed → rules |
|---|---|---|---|
| weak | 100% → 23% | 9% → 9% | 75% → 86% |
| medium | 8.5% → 21.5% | 26% → 11% | 73% → 84% |
| strong | 0% → 17% | 87% → 16% | 13% → 80% |

The shift is large for both extremes, which is the evidence Step 3 asked for.
The price is that the medium and strong bots now die sometimes. That is a
property of the baseline that Jev can be compared against.

## Run it

```bash
python -m scripts.step3_rules_baseline
```
