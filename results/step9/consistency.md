# Consistency (simulated Jev (FakeAnswers, noise 0.3), 30 repeats x 12 states)

|                     |   agreement |   worst_state |   distinct |
|:--------------------|------------:|--------------:|-----------:|
| ('async', 33.0)     |       1     |         1     |      1     |
| ('async', 100.0)    |       0.989 |         0.967 |      1.333 |
| ('async', 250.0)    |       0.506 |         0.367 |      4.333 |
| ('async', 500.0)    |       0.697 |         0.367 |      4.083 |
| ('blocking', nan)   |       0.706 |         0.367 |      3.833 |
| ('cache', 33.0)     |       0.969 |         0.967 |      1.917 |
| ('cache', 100.0)    |       0.969 |         0.967 |      1.917 |
| ('cache', 250.0)    |       0.986 |         0.967 |      1.417 |
| ('cache', 500.0)    |       0.997 |         0.967 |      1.083 |
| ('model', nan)      |       0.706 |         0.367 |      3.833 |
| ('prefetch', 33.0)  |       1     |         1     |      1     |
| ('prefetch', 100.0) |       1     |         1     |      1     |
| ('prefetch', 250.0) |       1     |         1     |      1     |
| ('prefetch', 500.0) |       1     |         1     |      1     |
| ('rules', nan)      |       1     |         1     |      1     |

agreement: share of repeats equal to the most common decision, mean over states.
