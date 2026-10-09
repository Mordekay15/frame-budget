# Step 10: analysis and figures

**Question:** what goes into the results chapter?

`scripts/step10_analyze.py` reads the Step 9 dataset and consistency file and
writes everything into `results/step10/`:

| file | content |
|---|---|
| `main_table.md`, `main_table.tex` | architecture × deadline with the four metrics, 95% confidence intervals, longest tick. The `.tex` is a booktabs table: `\usepackage{booktabs}`, then `\input{main_table.tex}` |
| `experience_table.md` | death rate, in-band and bored time per skill |
| `fig_deadline.png` | metric 1: share of decisions made by the model in time |
| `fig_fallback.png` | metric 2: share made by the rules instead |
| `fig_consistency.png` | metric 3: agreement for identical input |
| `fig_cost.png` | metric 4: USD per hour of play |
| `fig_tick.png` | longest tick per architecture: why blocking is ruled out |
| `fig_experience.png` | death rate per skill at the 250 ms deadline |

**The committed results are from the simulated Jev and synthetic latency.** They
show that the pipeline works and what shape the results have. They are not
thesis results until the sweep has been rerun with your measured latencies and
Jev's real answers (`docs/JEV_GUIDE.md`, part 7).

## What the simulated run already says (to be confirmed with real data)

1. **Blocking is ruled out**: the longest tick is about 740 ms, over 20 times the budget.
2. **With async, the deadline decides who is in charge**: below the median latency
   (~220 ms), Jev makes almost no decisions. The share follows the latency CDF from Step 0.
3. **Cache and prefetch move that curve up at tight deadlines**: prefetch gets about
   23% of decisions to Jev even at 33 ms, at about 2.7 times the requests.
4. **Async is the least consistent architecture** in the middle range (250 ms):
   the same state gets Jev's answer or the rules' depending on network luck.
   Cache and prefetch are the most consistent, because they reuse one answer.
5. **Cost is negligible in absolute terms**: around one to three US cents per hour of play.

## Notes on the statistics

- ± values are 95% confidence intervals of the mean over games (normal
  approximation, 1.96 · sd / √n). With 30 games per cell, death rates have wide
  intervals (about ±15 percentage points); use `--reps 100` in Step 9 if the
  experience results matter for your argument.
- Because of common random numbers (Step 9), paired comparisons between
  architectures (same skill and seed) are more powerful than comparing the
  two means independently. A paired test (e.g. Wilcoxon signed-rank on
  `deadline_met` per seed) is a good addition if your supervisor wants
  significance tests.

## Run it

```bash
python -m scripts.step10_analyze
```
