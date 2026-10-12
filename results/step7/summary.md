# Step 7: cached decisions (deadline 350 ms, latency=measured)

30 games per skill and coarseness; one shared cache per coarseness.

|   coarse |   hit_rate |   mismatch |   deadline_met |   fallback_rate |   requests_per_game |   cache_size |   death_rate |   hit_rate_2nd_half |
|---------:|-----------:|-----------:|---------------:|----------------:|--------------------:|-------------:|-------------:|--------------------:|
|     0.25 |      0.114 |      0.124 |          0.809 |           0.191 |              22.278 |         2005 |        0.211 |               0.162 |
|     0.5  |      0.411 |      0.235 |          0.868 |           0.132 |              14.056 |         1265 |        0.311 |               0.527 |
|     1    |      0.751 |      0.43  |          0.947 |           0.053 |               6.356 |          572 |        0.233 |               0.868 |
|     2    |      0.908 |      0.556 |          0.981 |           0.019 |               2.256 |          203 |        0.3   |               0.967 |
|     4    |      0.961 |      0.698 |          0.991 |           0.009 |               0.956 |           86 |        0.344 |               0.995 |
|     8    |      0.982 |      0.746 |          0.993 |           0.007 |               0.433 |           39 |        0.389 |               0.994 |

hit_rate_2nd_half: hit rate once the cache has warmed up (second half of the games).
mismatch: share of hits where a noise-free decider would choose differently for the exact state.
