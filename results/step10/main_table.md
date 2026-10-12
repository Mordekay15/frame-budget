# Architecture × deadline (1530 games, `results/step9/dataset.csv`)

| architecture | deadline | model decided in time | rules fallback | consistency | cost / hour | requests / hour | longest tick |
|---|---|---|---|---|---|---|---|
| rules | — | n/a | n/a | 1.00 | $0.0000 | 0 | 33 ms |
| blocking | — | 100% ± 0% | 0% ± 0% | 0.96 | $0.0267 | 985 | 649 ms |
| async | 33 ms | 0% ± 0% | 100% ± 0% | 1.00 | $0.0268 | 987 | 33 ms |
| async | 250 ms | 14% ± 2% | 86% ± 2% | 0.85 | $0.0267 | 984 | 33 ms |
| async | 350 ms | 81% ± 2% | 19% ± 2% | 0.81 | $0.0266 | 982 | 33 ms |
| async | 500 ms | 95% ± 1% | 5% ± 1% | 0.93 | $0.0267 | 986 | 33 ms |
| async | 750 ms | 100% ± 0% | 0% ± 0% | 0.96 | $0.0267 | 985 | 33 ms |
| cache | 33 ms | 9% ± 1% | 91% ± 1% | 0.97 | $0.0244 | 901 | 33 ms |
| cache | 250 ms | 22% ± 2% | 78% ± 2% | 0.98 | $0.0243 | 897 | 33 ms |
| cache | 350 ms | 83% ± 2% | 17% ± 2% | 0.99 | $0.0245 | 905 | 33 ms |
| cache | 500 ms | 95% ± 1% | 5% ± 1% | 1.00 | $0.0246 | 908 | 33 ms |
| cache | 750 ms | 100% ± 0% | 0% ± 0% | 1.00 | $0.0244 | 900 | 33 ms |
| prefetch | 33 ms | 24% ± 3% | 76% ± 3% | 1.00 | $0.0717 | 2646 | 33 ms |
| prefetch | 250 ms | 36% ± 3% | 64% ± 3% | 1.00 | $0.0715 | 2639 | 33 ms |
| prefetch | 350 ms | 87% ± 2% | 13% ± 2% | 1.00 | $0.0729 | 2693 | 33 ms |
| prefetch | 500 ms | 97% ± 1% | 3% ± 1% | 1.00 | $0.0722 | 2666 | 33 ms |
| prefetch | 750 ms | 100% ± 0% | 0% ± 0% | 1.00 | $0.0721 | 2664 | 33 ms |

± is the half-width of a 95% confidence interval over games. Consistency is the mean agreement
for identical input (1.00 = always the same decision). Cost is input tokens × $0.042 per million,
including prefetch requests. Longest tick is the worst single tick over all games.
