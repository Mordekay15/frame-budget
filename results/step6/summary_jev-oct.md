# Step 6: replay of `jev-oct`

Experiment: async + rules fallback, deadline 250 ms, 5 games per skill.

- replay 1 digest: `55800a2e21decf08`
- replay 2 digest: `55800a2e21decf08`
- **replays identical: True**
- recorded run digest: `55800a2e21decf08`, replay equals recorded run: **True**

| skill   |   deadline_met |   fallback_rate |   died |
|:--------|---------------:|----------------:|-------:|
| weak    |          0.682 |           0.318 |      1 |
| medium  |          0.621 |           0.379 |      0 |
| strong  |          0.648 |           0.352 |      0 |
