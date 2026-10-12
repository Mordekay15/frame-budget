# Consistency (simulated Jev (FakeAnswers, noise 0.1), 30 repeats x 12 states)

|                     |   agreement |   worst_state |   distinct |
|:--------------------|------------:|--------------:|-----------:|
| ('async', 33.0)     |       1     |         1     |      1     |
| ('async', 250.0)    |       0.85  |         0.767 |      1.917 |
| ('async', 350.0)    |       0.806 |         0.7   |      2.333 |
| ('async', 500.0)    |       0.931 |         0.733 |      2.083 |
| ('async', 750.0)    |       0.964 |         0.8   |      1.583 |
| ('blocking', nan)   |       0.964 |         0.8   |      1.583 |
| ('cache', 33.0)     |       0.969 |         0.967 |      1.917 |
| ('cache', 250.0)    |       0.975 |         0.967 |      1.75  |
| ('cache', 350.0)    |       0.992 |         0.967 |      1.25  |
| ('cache', 500.0)    |       1     |         1     |      1     |
| ('cache', 750.0)    |       1     |         1     |      1     |
| ('model', nan)      |       0.964 |         0.8   |      1.583 |
| ('prefetch', 33.0)  |       1     |         1     |      1     |
| ('prefetch', 250.0) |       1     |         1     |      1     |
| ('prefetch', 350.0) |       1     |         1     |      1     |
| ('prefetch', 500.0) |       1     |         1     |      1     |
| ('prefetch', 750.0) |       1     |         1     |      1     |
| ('rules', nan)      |       1     |         1     |      1     |

agreement: share of repeats equal to the most common decision, mean over states.
