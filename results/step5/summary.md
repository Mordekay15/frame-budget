# Step 5: async with rules fallback (simulated Jev and clock, latency=measured)

|   budget_ms |   games |   deadline_met |   fallback_rate |   late |   stale |   failed |   tick_p99_ms |   tick_max_ms |   overruns |   death_rate |
|------------:|--------:|---------------:|----------------:|-------:|--------:|---------:|--------------:|--------------:|-----------:|-------------:|
|          33 |     150 |          0     |           1     |   3892 |       0 |        0 |            33 |            33 |          0 |        0.187 |
|         250 |     150 |          0.14  |           0.86  |   3439 |       0 |        0 |            33 |            33 |          0 |        0.167 |
|         350 |     150 |          0.791 |           0.209 |    798 |       0 |        0 |            33 |            33 |          0 |        0.247 |
|         500 |     150 |          0.937 |           0.063 |    243 |       0 |        0 |            33 |            33 |          0 |        0.213 |
|         750 |     150 |          1     |           0     |      0 |       0 |        0 |            33 |            33 |          0 |        0.253 |

deadline_met: share of decisions where Jev's answer arrived within the budget and was used.
fallback_rate: share where the rules decided instead. late/stale/failed: discarded answers.
tick_max_ms is the longest tick: it stays at the 33 ms budget (on the simulated clock exactly,
on the real clock within the jitter measured in Step 1).
