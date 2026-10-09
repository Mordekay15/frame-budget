# Architecture × deadline (1260 games, `results/step9/dataset.csv`)

| architecture | deadline | model decided in time | rules fallback | consistency | cost / hour | requests / hour | longest tick |
|---|---|---|---|---|---|---|---|
| rules | — | n/a | n/a | 1.00 | $0.0000 | 0 | 33 ms |
| blocking | — | 100% ± 0% | 0% ± 0% | 0.71 | $0.0104 | 994 | 738 ms |
| async | 33 ms | 0% ± 0% | 100% ± 0% | 1.00 | $0.0104 | 987 | 33 ms |
| async | 100 ms | 2% ± 1% | 98% ± 1% | 0.99 | $0.0104 | 986 | 33 ms |
| async | 250 ms | 67% ± 2% | 33% ± 2% | 0.51 | $0.0104 | 991 | 33 ms |
| async | 500 ms | 99% ± 1% | 1% ± 1% | 0.70 | $0.0104 | 989 | 33 ms |
| cache | 33 ms | 9% ± 1% | 91% ± 1% | 0.97 | $0.0095 | 901 | 33 ms |
| cache | 100 ms | 10% ± 2% | 90% ± 2% | 0.97 | $0.0095 | 899 | 33 ms |
| cache | 250 ms | 70% ± 2% | 30% ± 2% | 0.99 | $0.0096 | 917 | 33 ms |
| cache | 500 ms | 99% ± 1% | 1% ± 1% | 1.00 | $0.0097 | 919 | 33 ms |
| prefetch | 33 ms | 23% ± 3% | 77% ± 3% | 1.00 | $0.0285 | 2707 | 33 ms |
| prefetch | 100 ms | 24% ± 2% | 76% ± 2% | 1.00 | $0.0285 | 2712 | 33 ms |
| prefetch | 250 ms | 73% ± 2% | 27% ± 2% | 1.00 | $0.0291 | 2769 | 33 ms |
| prefetch | 500 ms | 99% ± 0% | 1% ± 0% | 1.00 | $0.0293 | 2785 | 33 ms |

± is the half-width of a 95% confidence interval over games. Consistency is the mean agreement
for identical input (1.00 = always the same decision). Cost is input tokens × $0.042 per million,
including prefetch requests. Longest tick is the worst single tick over all games.
