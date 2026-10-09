# Step 4: blocking architecture (simulated Jev, latency=synthetic)

| arch     |   games |   tick_p99_ms |   tick_max_ms |   blowout_mean |   blowout_max |   overruns_per_game |
|:---------|--------:|--------------:|--------------:|---------------:|--------------:|--------------------:|
| blocking |     150 |         63.05 |        760.96 |          12.06 |         23.06 |               18.62 |
| rules    |     150 |         33    |         33    |           1    |          1    |                0    |

Budget per tick: 33 ms. Every decision point in a blocking game is an overrun: 2793 overruns in 2793 decisions.

**Blowout factor** = longest tick / 33 ms. Mean over games: 12.1x, worst game: 23.1x.
