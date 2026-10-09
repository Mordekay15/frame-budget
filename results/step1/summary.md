# Step 1: bare loop

Machine: Linux-6.18.44-fc-v80-x86_64-with-glibc2.39, Python 3.13.16

| metric | value |
|---|---|
| ticks | 10000 |
| period_mean_ms | 33.0000 |
| period_std_ms | 0.2157 |
| period_p50_ms | 33.0000 |
| period_p99_ms | 33.2197 |
| period_max_ms | 44.0983 |
| work_max_ms | 0.1252 |
| lateness_max_ms | 11.0993 |
| final_drift_ms | 0.0021 |
| overruns | 0 |
| blowout_factor | 1.3363 |

`final_drift_ms` is how far the last tick started from its schedule. With an absolute
schedule it stays bounded instead of growing with the number of ticks.
