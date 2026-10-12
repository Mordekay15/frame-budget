# Step 4: blocking architecture (LIVE Jev, real clock)

| arch     |   games |   tick_p99_ms |   tick_max_ms |   blowout_mean |   blowout_max |   overruns_per_game |
|:---------|--------:|--------------:|--------------:|---------------:|--------------:|--------------------:|
| blocking |       3 |        107.35 |        349.18 |           9.62 |         10.58 |               28.33 |
| rules    |       3 |         33    |         33    |           1    |          1    |                0    |

Budget per tick: 33 ms. Every decision point in a blocking game is an overrun: 85 overruns in 85 decisions.

**Blowout factor** = longest tick / 33 ms. Mean over games: 9.6x, worst game: 10.6x.
