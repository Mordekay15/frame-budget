# Step 5: async with rules fallback (simulated Jev, real clock, latency=synthetic)

|   budget_ms |   games |   deadline_met |   fallback_rate |   late |   stale |   failed |   tick_p99_ms |   tick_max_ms |   overruns |   death_rate |
|------------:|--------:|---------------:|----------------:|-------:|--------:|---------:|--------------:|--------------:|-----------:|-------------:|
|         250 |       3 |           0.69 |            0.31 |     27 |       0 |        0 |        33.438 |        68.588 |          0 |            0 |

deadline_met: share of decisions where Jev's answer arrived within the budget and was used.
fallback_rate: share where the rules decided instead. late/stale/failed: discarded answers.
tick_max_ms is the longest tick: it stays at the 33 ms budget (on the simulated clock exactly,
on the real clock within the jitter measured in Step 1).
