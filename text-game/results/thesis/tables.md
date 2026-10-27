# Results tables

From `results/sim/live-20261027_0720` (255 games, 8419 spells) and 3 Step 0 runs (1710 requests). Made by analysis/results.py.

## Jev latency on the spell request (Step 0, and live during the sweep)

| condition | n | errors | median | p95 | max | ≤ 33 | ≤ 100 | ≤ 167 | ≤ 200 | ≤ 233 | ≤ 333 | ≤ 500 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| warm | 900 | 0 | 194 ms | 254 ms | 504 ms | 0% | 0% | 26% | 63% | 91% | 99% | 100% |
| cold | 300 | 0 | 202 ms | 302 ms | 402 ms | 0% | 0% | 0% | 46% | 84% | 100% | 100% |
| same | 270 | 0 | 196 ms | 302 ms | 450 ms | 0% | 0% | 28% | 61% | 88% | 99% | 100% |
| long | 150 | 0 | 197 ms | 283 ms | 430 ms | 0% | 0% | 19% | 58% | 87% | 98% | 100% |
| inject | 90 | 0 | 200 ms | 291 ms | 426 ms | 0% | 0% | 32% | 50% | 88% | 98% | 100% |
| during the sweep | 12345 | 0 | 204 ms | 307 ms | 1082 ms | 0% | 0% | 17% | 26% | 85% | 98% | 100% |

Failures count as misses. 'during the sweep' = every answer the live sweep received.

## Agreement with the corpus labels (Step 0, warm and cold)

| question | Jev | keyword rules |
|---|---|---|
| element | 95% | 60% |
| target | 88% | 86% |
| power | 82% | 60% |

1200 labelled requests. Format validity: 1710 of 1710 answers parsed (100%).

## Architectures by deadline (live Jev, all skills pooled)

| architecture | deadline (frames) | decided by model | mean wait | p95 wait | requests / spell | element right | rules on same spells | cost / hour | worst tick |
|---|---|---|---|---|---|---|---|---|---|
| rules | – | 0% ± 0 | 0 ms | 0 ms | – | 67% | 67% | $0.000 | 33 ms |
| blocking | – | 100% ± 0 | 211 ms | 304 ms | 1.00 | 95% | 61% | $0.012 | 475 ms |
| async | 33 ms (1) | 0% ± 0 | 33 ms | 33 ms | 1.00 | 67% | 67% | $0.012 | 33 ms |
| async | 167 ms (5) | 12% ± 4 | 167 ms | 167 ms | 1.00 | 72% | 68% | $0.012 | 33 ms |
| async | 200 ms (6) | 20% ± 5 | 196 ms | 200 ms | 1.00 | 72% | 68% | $0.012 | 33 ms |
| async | 233 ms (7) | 84% ± 4 | 221 ms | 233 ms | 1.00 | 86% | 58% | $0.012 | 33 ms |
| async | 333 ms (10) | 98% ± 1 | 230 ms | 316 ms | 1.00 | 93% | 60% | $0.012 | 33 ms |
| cache | 33 ms (1) | 35% ± 6 | 22 ms | 33 ms | 0.62 | 73% | 64% | $0.007 | 33 ms |
| cache | 167 ms (5) | 43% ± 8 | 106 ms | 167 ms | 0.58 | 77% | 63% | $0.007 | 33 ms |
| cache | 200 ms (6) | 46% ± 6 | 136 ms | 200 ms | 0.63 | 78% | 66% | $0.008 | 33 ms |
| cache | 233 ms (7) | 91% ± 3 | 135 ms | 233 ms | 0.57 | 90% | 61% | $0.007 | 33 ms |
| cache | 333 ms (10) | 98% ± 2 | 143 ms | 296 ms | 0.56 | 94% | 61% | $0.007 | 33 ms |
| prefetch | 33 ms (1) | 68% ± 7 | 12 ms | 33 ms | 2.88 | 85% | 61% | $0.049 | 33 ms |
| prefetch | 167 ms (5) | 87% ± 5 | 45 ms | 162 ms | 3.04 | 91% | 62% | $0.050 | 33 ms |
| prefetch | 200 ms (6) | 91% ± 5 | 50 ms | 193 ms | 3.12 | 92% | 62% | $0.051 | 33 ms |
| prefetch | 233 ms (7) | 97% ± 1 | 57 ms | 224 ms | 3.13 | 92% | 61% | $0.051 | 33 ms |
| prefetch | 333 ms (10) | 100% ± 1 | 59 ms | 236 ms | 3.15 | 94% | 63% | $0.051 | 33 ms |

Mean over games with a 95% CI over games. Requests include prefetches. The tick budget is 33 ms.

## Share decided by the model, by player skill

| architecture | deadline (frames) | weak | average | strong |
|---|---|---|---|---|
| async | 33 ms (1) | 0% | 0% | 0% |
| async | 167 ms (5) | 16% | 12% | 9% |
| async | 200 ms (6) | 15% | 22% | 22% |
| async | 233 ms (7) | 80% | 86% | 86% |
| async | 333 ms (10) | 98% | 100% | 98% |
| cache | 33 ms (1) | 25% | 36% | 43% |
| cache | 167 ms (5) | 32% | 41% | 54% |
| cache | 200 ms (6) | 38% | 48% | 53% |
| cache | 233 ms (7) | 94% | 89% | 89% |
| cache | 333 ms (10) | 98% | 97% | 99% |
| prefetch | 33 ms (1) | 57% | 68% | 78% |
| prefetch | 167 ms (5) | 77% | 86% | 98% |
| prefetch | 200 ms (6) | 80% | 94% | 97% |
| prefetch | 233 ms (7) | 96% | 99% | 96% |
| prefetch | 333 ms (10) | 100% | 99% | 99% |

Stronger bot players reuse spells more often (30% against 10%), so cache and prefetch find more answers already there.

## Game outcome (deadline 200 ms)

| architecture | deadline (frames) | games won | hearts left | gloomlings beaten |
|---|---|---|---|---|
| rules | – | 0% | 0.0 | 12.0 |
| blocking | – | 20% | 0.5 | 22.2 |
| async | 200 ms (6) | 0% | 0.0 | 15.0 |
| cache | 200 ms (6) | 7% | 0.1 | 14.8 |
| prefetch | 200 ms (6) | 7% | 0.1 | 19.2 |

Outcome depends on the bot as much as on the decisions; reported for completeness.
