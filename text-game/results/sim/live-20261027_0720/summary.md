# Simulation summary

Decider: **live** (live). 255 games. Seed 1, cache key coarseness 1.

| architecture | deadline | games | decided by model (95% CI) | fallback | mean wait | p95 wait | requests / spell | element right | rules would be right | cost / hour | worst tick |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rules | – | 15 | 0% ± 0 | 100% | 0 ms | 0 ms | 0.00 | 67% | 67% | $0.000 | 33 ms |
| blocking | – | 15 | 100% ± 0 | 0% | 211 ms | 304 ms | 1.00 | 95% | 61% | $0.012 | 475 ms |
| async | 33 ms | 15 | 0% ± 0 | 100% | 33 ms | 33 ms | 1.00 | 67% | 67% | $0.012 | 33 ms |
| async | 167 ms | 15 | 12% ± 4 | 88% | 167 ms | 167 ms | 1.00 | 72% | 68% | $0.012 | 33 ms |
| async | 200 ms | 15 | 20% ± 5 | 80% | 196 ms | 200 ms | 1.00 | 72% | 68% | $0.012 | 33 ms |
| async | 233 ms | 15 | 84% ± 4 | 16% | 221 ms | 233 ms | 1.00 | 86% | 58% | $0.012 | 33 ms |
| async | 333 ms | 15 | 98% ± 1 | 2% | 230 ms | 316 ms | 1.00 | 93% | 60% | $0.012 | 33 ms |
| cache | 33 ms | 15 | 35% ± 6 | 65% | 22 ms | 33 ms | 0.62 | 73% | 64% | $0.007 | 33 ms |
| cache | 167 ms | 15 | 43% ± 8 | 57% | 106 ms | 167 ms | 0.58 | 77% | 63% | $0.007 | 33 ms |
| cache | 200 ms | 15 | 46% ± 6 | 54% | 136 ms | 200 ms | 0.63 | 78% | 66% | $0.008 | 33 ms |
| cache | 233 ms | 15 | 91% ± 3 | 9% | 135 ms | 233 ms | 0.57 | 90% | 61% | $0.007 | 33 ms |
| cache | 333 ms | 15 | 98% ± 2 | 2% | 143 ms | 296 ms | 0.56 | 94% | 61% | $0.007 | 33 ms |
| prefetch | 33 ms | 15 | 68% ± 7 | 32% | 12 ms | 33 ms | 2.88 | 85% | 61% | $0.049 | 33 ms |
| prefetch | 167 ms | 15 | 87% ± 5 | 13% | 45 ms | 162 ms | 3.04 | 91% | 62% | $0.050 | 33 ms |
| prefetch | 200 ms | 15 | 91% ± 5 | 9% | 50 ms | 193 ms | 3.12 | 92% | 62% | $0.051 | 33 ms |
| prefetch | 233 ms | 15 | 97% ± 1 | 3% | 57 ms | 224 ms | 3.13 | 92% | 61% | $0.051 | 33 ms |
| prefetch | 333 ms | 15 | 100% ± 1 | 0% | 59 ms | 236 ms | 3.15 | 94% | 63% | $0.051 | 33 ms |

- **decided by model**: share of spells decided by Jev, the cache or a prefetch, i.e. not by the fallback rules.
- **wait**: from pressing Enter to the spell being cast. Rules and cache hits are instant.
- **element right**: the applied element matches the corpus label (labelled spells only). **rules would be right**: the same for the keyword rules on the same spells.
- **worst tick**: the longest tick in any game of the row. The budget is 33 ms; only blocking breaks it.
