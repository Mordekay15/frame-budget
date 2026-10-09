# Step 3: rules (Hunicke comfort zone) vs fixed difficulty

200 games per skill and policy, same seeds for both policies.

|                     |   death_rate |   waves |   bored |   in_band |   danger |
|:--------------------|-------------:|--------:|--------:|----------:|---------:|
| ('weak', 'fixed')   |        1     |   8.115 |   0.088 |     0.754 |    0.159 |
| ('weak', 'rules')   |        0.23  |  25.36  |   0.092 |     0.855 |    0.053 |
| ('medium', 'fixed') |        0.085 |  29.23  |   0.259 |     0.726 |    0.015 |
| ('medium', 'rules') |        0.215 |  26.435 |   0.11  |     0.839 |    0.051 |
| ('strong', 'fixed') |        0     |  30     |   0.869 |     0.131 |    0     |
| ('strong', 'rules') |        0.17  |  27.525 |   0.158 |     0.799 |    0.044 |

## Shift (rules minus fixed)

| skill   |   death_rate |   waves |   bored |   in_band |   danger |
|:--------|-------------:|--------:|--------:|----------:|---------:|
| weak    |        -0.77 |  17.245 |   0.004 |     0.101 |   -0.106 |
| medium  |         0.13 |  -2.795 |  -0.149 |     0.113 |    0.036 |
| strong  |         0.17 |  -2.475 |  -0.711 |     0.668 |    0.044 |
