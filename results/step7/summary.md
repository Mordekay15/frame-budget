# Step 7: cached decisions (deadline 250 ms, latency=synthetic)

30 games per skill and coarseness; one shared cache per coarseness.

|   coarse |   hit_rate |   mismatch |   deadline_met |   fallback_rate |   requests_per_game |   cache_size |   death_rate |   hit_rate_2nd_half |
|---------:|-----------:|-----------:|---------------:|----------------:|--------------------:|-------------:|-------------:|--------------------:|
|     0.25 |      0.109 |      0.149 |          0.698 |           0.302 |              22.578 |         2032 |        0.278 |               0.158 |
|     0.5  |      0.428 |      0.25  |          0.814 |           0.186 |              14.689 |         1322 |        0.222 |               0.574 |
|     1    |      0.75  |      0.418 |          0.923 |           0.077 |               6.333 |          570 |        0.233 |               0.873 |
|     2    |      0.904 |      0.556 |          0.974 |           0.026 |               2.444 |          220 |        0.222 |               0.966 |
|     4    |      0.961 |      0.684 |          0.989 |           0.011 |               0.956 |           86 |        0.311 |               0.99  |
|     8    |      0.984 |      0.75  |          0.995 |           0.005 |               0.389 |           35 |        0.378 |               0.997 |

hit_rate_2nd_half: hit rate once the cache has warmed up (second half of the games).
mismatch: share of hits where a noise-free decider would choose differently for the exact state.
