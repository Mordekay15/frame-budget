# Step 0 results: jev_latency.csv

Served by: jev-1.13.0  
First request: 2026-10-12T12:24:36.504+00:00  
Last request: 2026-10-12T12:28:30.361+00:00

## Latency

| condition   |   n |   errors |   median_ms |   p95_ms |   p99_ms |   max_ms | under_33ms   | under_250ms   | under_350ms   | under_500ms   |
|:------------|----:|---------:|------------:|---------:|---------:|---------:|:-------------|:--------------|:--------------|:--------------|
| warm        | 300 |        0 |         310 |      506 |      617 |      649 | 0%           | 14%           | 80%           | 95%           |
| cold        | 100 |        0 |         412 |      550 |      630 |     1229 | 0%           | 0%            | 27%           | 86%           |
| same        |  30 |        0 |         311 |      516 |      574 |      598 | 0%           | 13%           | 70%           | 90%           |

`under_Xms` is the share of requests that succeeded within X ms, i.e. how often a
decision with that deadline would have arrived in time.

## Cost

Mean input tokens per request: 646. Cost reported by the API for this run: $0.01167.
At one decision every 5 s, an hour of play is 720 requests, about $0.0195.

## Consistency (same state repeated)

30 requests with one identical state.

- `count` answers: 8: 100%
  - largest std of a probability across repeats: 0.0165
- `mult` answers: 1.0: 97%, 0.75: 3%
  - largest std of a probability across repeats: 0.0397
