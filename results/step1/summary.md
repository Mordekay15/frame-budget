# Step 1: bare loop

Machine: Windows-11-10.0.22631-SP0, Python 3.12.1

| metric | value |
|---|---|
| ticks | 10000 |
| period_mean_ms | 33.0000 |
| period_std_ms | 1.6197 |
| period_p50_ms | 33.0000 |
| period_p99_ms | 33.0189 |
| period_max_ms | 63.8756 |
| work_max_ms | 15.5374 |
| lateness_max_ms | 30.8780 |
| final_drift_ms | 0.0028 |
| overruns | 0 |
| blowout_factor | 1.9356 |

`final_drift_ms` is how far the last tick started from its schedule. With an absolute
schedule it stays bounded instead of growing with the number of ticks.
