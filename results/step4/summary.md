# Step 4: blocking architecture (simulated Jev, latency=measured)

| arch     |   games |   tick_p99_ms |   tick_max_ms |   blowout_mean |   blowout_max |   overruns_per_game |
|:---------|--------:|--------------:|--------------:|---------------:|--------------:|--------------------:|
| blocking |     150 |         98.69 |        649.12 |          16.03 |         19.67 |               24.79 |
| rules    |     150 |         33    |         33    |           1    |          1    |                0    |

Budget per tick: 33 ms. Every decision point in a blocking game is an overrun: 3718 overruns in 3718 decisions.

**Blowout factor** = longest tick / 33 ms. Mean over games: 16.0x, worst game: 19.7x.
