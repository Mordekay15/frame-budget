# Step 6: replay of `synthetic-demo`

Experiment: async + rules fallback, deadline 250 ms, 5 games per skill.

- replay 1 digest: `4e0ee6b3de587a6c`
- replay 2 digest: `4e0ee6b3de587a6c`
- **replays identical: True**
- recorded run digest: `4e0ee6b3de587a6c`, replay equals recorded run: **True**

| skill   |   deadline_met |   fallback_rate |   died |
|:--------|---------------:|----------------:|-------:|
| weak    |          0.62  |           0.38  |    0.2 |
| medium  |          0.6   |           0.4   |    0   |
| strong  |          0.662 |           0.338 |    0.2 |
