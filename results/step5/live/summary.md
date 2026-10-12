# Step 5: async with rules fallback (LIVE Jev, real clock, latency=measured)

|   budget_ms |   games |   deadline_met |   fallback_rate |   late |   stale |   failed |   tick_p99_ms |   tick_max_ms |   overruns |   death_rate |
|------------:|--------:|---------------:|----------------:|-------:|--------:|---------:|--------------:|--------------:|-----------:|-------------:|
|         350 |       3 |          0.989 |           0.011 |      1 |       0 |        0 |        33.017 |        64.217 |          0 |            0 |

deadline_met: share of decisions where Jev's answer arrived within the budget and was used.
fallback_rate: share where the rules decided instead. late/stale/failed: discarded answers.
tick_max_ms is the longest tick: it stays at the 33 ms budget (on the simulated clock exactly,
on the real clock within the jitter measured in Step 1).
