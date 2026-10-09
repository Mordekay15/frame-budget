# Step 5: async with rules fallback (simulated Jev and clock, latency=synthetic)

|   budget_ms |   games |   deadline_met |   fallback_rate |   late |   stale |   failed |   tick_p99_ms |   tick_max_ms |   overruns |   death_rate |
|------------:|--------:|---------------:|----------------:|-------:|--------:|---------:|--------------:|--------------:|-----------:|-------------:|
|          33 |     150 |          0     |           1     |   3892 |       0 |        0 |            33 |            33 |          0 |        0.187 |
|         100 |     150 |          0.013 |           0.987 |   3859 |       0 |        0 |            33 |            33 |          0 |        0.18  |
|         250 |     150 |          0.662 |           0.338 |   1392 |       0 |        0 |            33 |            33 |          0 |        0.147 |
|         500 |     150 |          0.995 |           0.005 |     20 |       0 |        0 |            33 |            33 |          0 |        0.227 |

deadline_met: share of decisions where Jev's answer arrived within the budget and was used.
fallback_rate: share where the rules decided instead. late/stale/failed: discarded answers.
tick_max_ms is the longest tick: it stays at the 33 ms budget (on the simulated clock exactly,
on the real clock within the jitter measured in Step 1).
