# Robustness, Ablation, and Parameter Sensitivity in EuroMillions Strategy Backtesting

## Abstract

This paper extends the Millionaire Project's initial ranked-ticket modelling work with a deeper robustness analysis. The original model introduced a walk-forward backtest for comparing a ranked EuroMillions ticket strategy against simpler baselines. This second analysis asks whether the ranked model's apparent advantages survive more careful evaluation. It adds prize-tier analysis, confidence intervals, repeated-seed robustness checks, theoretical prize probabilities, total-match distributions, model ablation, and a wider parameter grid. Results show small but interesting exploratory signals: the ranked model produced more prize-tier hits than the random baseline in the default 200-draw backtest, and it maintained a small positive edge across a 10-seed robustness test. Ablation results suggest that the hot-number component contributes meaningful signal in the tested window, while the spread component may be over-constraining ticket selection. However, confidence intervals remain wide, sample sizes are limited, and all results remain close to the mathematical random baseline.

## 1. Introduction

The first modelling paper established the core ranked-ticket method and its walk-forward backtest. That work was intentionally conservative: it compared strategies using only historical information available before each tested draw and emphasized that lottery draws are designed to be random.

This paper takes the next step. Rather than asking only whether the ranked model can outperform simple baselines in one backtest, it asks whether the model's behavior is stable under richer evaluation. The goal is to distinguish three possibilities:

1. the ranked model contains useful but weak structure;
2. the apparent gains are mostly noise from one historical window;
3. the scoring formula is decorative and does not improve over simpler strategies.

The analysis remains exploratory. It does not claim that EuroMillions can be predicted. Instead, it treats the model as a strategy-construction rule and studies how that rule behaves under historical replay.

## 2. Data and Baseline

The analysis uses the same master dataset as the first paper: 1,958 EuroMillions draws from 13 February 2004 through 26 June 2026. Each draw contains five main balls from 1 to 50 and two Lucky Stars from 1 to 12.

The theoretical random baseline is central. A random ticket has expected matches:

```text
Expected ball matches = 5 * (5 / 50) = 0.500
Expected star matches = 2 * (2 / 12) = 0.333
Expected total matches = 0.833
```

Prize-tier probabilities also keep the results grounded. The lowest prize tier, 2+0, has odds of about 1 in 21.9. The jackpot tier, 5+2, has odds of about 1 in 139.8 million.

## 3. Methods

### 3.1 Prize-Tier Analysis

The first backtest counted total matches. This paper adds EuroMillions prize-tier classification. A ticket is classified by its main-ball and Lucky Star matches:

```text
5+2, 5+1, 5+0, 4+2, 4+1, 3+2, 4+0,
2+2, 3+1, 3+0, 1+2, 2+1, 2+0
```

This matters because total matches can hide different practical outcomes. For example, 2+1 is a prize tier, while some other equal-total combinations may not be equivalent.

### 3.2 Confidence Intervals

The analysis reports confidence intervals for average total matches and prize-hit rates. These intervals are used to avoid overinterpreting small differences between strategies, especially when the observed edge is close to random expectation.

### 3.3 Repeated-Seed Robustness

The repeated-seed test reruns the backtest under different random seeds. This checks whether the ranked model's outcome depends heavily on one candidate-generation sequence.

The saved repeated-seed run used:

- 10 seeds;
- 75 test draws;
- 100 ranked candidates per tested draw;
- 300-draw training window;
- 100-draw recent window;
- 75-draw half-life.

### 3.4 Match-Distribution Analysis

Average total matches can be misleading. A strategy with the same average as random might still produce fewer complete misses, more two-match tickets, or a different high-match tail. The distribution analysis therefore reports:

- percentage of tickets with zero total matches;
- percentage with one match;
- percentage with two matches;
- percentage with three or more matches;
- maximum total matches;
- standard deviation of total matches.

### 3.5 Model Ablation

The ranked model combines five components:

- hot score;
- cold score;
- balance score;
- spread score;
- pair score.

The ablation study tests whether each component is useful by removing or isolating components. The variants are:

- full model;
- no hot score;
- no cold score;
- no balance score;
- no spread score;
- no pair score;
- only hot score;
- only pair score;
- only balance/spread.

The saved ablation run used 50 test draws, 100 candidate tickets per draw, and a 75-draw half-life.

### 3.6 Wider Parameter Grid

The wider bounded grid varies:

- recency half-life;
- simulation count;
- rolling training-history size;
- recent-window size.

The saved sweep includes half-lives of 25, 75, 150, and 250 draws; simulation counts of 100 and 300; rolling training windows of 100 and 300 draws; and recent windows of 50 and 100 draws.

The ranked model's scoring function currently uses recency-weighted history and pair history. The recent-window dimension is still useful for comparing other strategies, but it does not directly change the ranked model unless recent-window dependence is added to the ranked score.

## 4. Results

### 4.1 Default Backtest With Prize Tiers

In the default 200-draw backtest, the ranked model achieved 19 prize-tier hits, a 9.5% hit rate. The random baseline achieved 15 hits, a 7.5% hit rate.

| Strategy | Draws | Avg total matches | 95% CI | Prize hits | Prize-hit rate | Best prize tier |
|---|---:|---:|---|---:|---:|---|
| Ranked model | 200 | 0.820 | 0.716-0.924 | 19 | 9.5% | 2+1 |
| Random baseline | 200 | 0.835 | 0.726-0.944 | 15 | 7.5% | 2+2 |
| Cold numbers | 200 | 0.760 | 0.650-0.870 | 15 | 7.5% | 3+0 |
| Balanced mix | 200 | 0.795 | 0.692-0.898 | 11 | 5.5% | 1+2 |
| Recent hot | 200 | 0.770 | 0.664-0.876 | 8 | 4.0% | 3+0 |

The ranked model produced more prize-tier hits than random in this run, but the average-match confidence intervals overlap substantially. This is a useful signal, not a decisive result.

### 4.2 Repeated-Seed Robustness

Across 10 repeated-seed runs, the ranked model averaged 0.867 total matches and a 9.6% prize-hit rate. The random baseline averaged 0.844 total matches and an 8.7% prize-hit rate.

| Strategy | Runs | Mean total matches | 95% CI | Mean prize-hit rate | Win rate vs random | Avg total edge vs random |
|---|---:|---:|---|---:|---:|---:|
| Ranked model | 10 | 0.867 | 0.809-0.925 | 9.6% | 60.0% | 0.023 |
| Random baseline | 10 | 0.844 | 0.805-0.883 | 8.7% | - | - |
| Recent hot | 10 | 0.877 | 0.818-0.936 | 8.0% | 60.0% | 0.033 |
| Balanced mix | 10 | 0.853 | 0.786-0.921 | 7.3% | 60.0% | 0.009 |
| Cold numbers | 10 | 0.773 | 0.737-0.810 | 6.4% | 0.0% | -0.071 |

The ranked model's edge is positive but small. It did not dominate the repeated setting, and recent-hot numbers achieved a slightly higher average total match rate while producing a lower prize-hit rate.

### 4.3 Match-Distribution Results

In the default 200-draw backtest, the ranked model reduced complete misses slightly compared with random, but it did not improve the high-match tail.

| Strategy | 0 matches | 1 match | 2 matches | 3+ matches | Max total matches |
|---|---:|---:|---:|---:|---:|
| Ranked model | 36.5% | 47.0% | 14.5% | 2.0% | 3 |
| Random baseline | 37.5% | 44.0% | 16.5% | 2.0% | 4 |
| Cold numbers | 43.5% | 39.5% | 14.5% | 2.5% | 3 |
| Recent hot | 41.0% | 43.0% | 14.0% | 2.0% | 3 |
| Balanced mix | 39.5% | 42.0% | 18.0% | 0.5% | 3 |

This distribution is a useful caution. The ranked model looks steadier than random in complete-miss rate, but it did not produce more three-plus-match outcomes in the default window.

### 4.4 Ablation Results

The ablation test suggests that the hot component matters most in the current scoring design.

| Variant | Draws | Avg total matches | Prize-hit rate | Best prize tier |
|---|---:|---:|---:|---|
| No spread score | 50 | 1.020 | 14.0% | 2+2 |
| Full model | 50 | 1.000 | 12.0% | 2+2 |
| No balance score | 50 | 0.780 | 12.0% | 2+2 |
| No cold score | 50 | 0.900 | 10.0% | 2+2 |
| Only hot score | 50 | 0.840 | 10.0% | 2+2 |
| No pair score | 50 | 0.880 | 6.0% | 2+2 |
| No hot score | 50 | 0.660 | 4.0% | 2+2 |
| Only pair score | 50 | 0.660 | 4.0% | 2+1 |
| Only balance/spread | 50 | 0.580 | 0.0% | No prize |

Removing the spread component slightly improved the short-window result. Removing hot score sharply reduced performance. The balance/spread-only model performed worst by prize-hit rate, producing no prize-tier hits in this run.

These results suggest that hot-score information is doing meaningful work, while spread may be too restrictive. However, the ablation window is only 50 draws, so these findings should be treated as hypotheses for larger repeated tests.

### 4.5 Wider Parameter Grid

The strongest saved grid cell used:

- half-life: 250 draws;
- simulations: 100;
- rolling training history: 300 draws;
- recent window: 50 or 100 draws;
- test window: 75 draws.

It achieved:

- average total matches: 1.053;
- prize-hit rate: 16.0%;
- three-plus match rate: 8.0%;
- best prize tier: 2+2.

The top rows favored longer half-lives and fewer simulations in this bounded sweep. That does not mean fewer simulations are inherently better; it may mean that, for this sample and scoring function, the highest-scoring candidate among a larger random candidate pool can overfit the heuristic score rather than improve historical matching.

## 5. Discussion

The extended analysis strengthens the project in two ways. First, it makes evaluation less dependent on a single average-match metric. Prize tiers, confidence intervals, repeated seeds, and match distributions provide a more complete view of strategy behavior. Second, ablation begins to explain the ranked model rather than merely report its score.

The evidence remains mixed. The ranked model produced more prize-tier hits than random in the default run and maintained a small positive edge in repeated-seed testing. But the advantage is small, confidence intervals overlap random, and some simple strategies are competitive on average matches.

The ablation result is the clearest modelling insight. Hot-score removal hurt performance, while spread removal slightly improved it in the tested window. This suggests a concrete next experiment: reduce or remove spread weight, then rerun repeated-seed and long-window tests.

The wider grid also surfaces an implementation detail. Recent-window settings do not currently affect the ranked model directly. They matter for recent-hot and balanced-mix strategies, but the ranked model uses recency-weighted history through the half-life parameter. Future ranked-model variants should either remove recent-window from ranked-model sweeps or add a recent-window feature explicitly.

## 6. Limitations

The main limitation is the randomness of the underlying process. EuroMillions draws are not expected to contain stable exploitable structure. Historical replay can compare strategy rules, but it cannot prove future predictive power.

The ablation test is short, at 50 draws. The repeated-seed test uses only 10 seeds. The wider parameter grid is bounded to keep compute time manageable. These choices are appropriate for exploratory analysis, but the next stage should increase seeds, expand test windows, and optimize computation before treating any result as robust.

Payout-weighted expected value is handled in a third companion paper. Prize-hit rate remains useful here, but it is not the final value metric because not all prize tiers have equal value.

## 7. Conclusion

The further analysis supports a careful conclusion. The ranked model shows small exploratory advantages in some settings, especially in prize-hit rate and complete-miss reduction, but those advantages remain close to random expectation. The model's hot-score component appears important, while spread may deserve less weight. Longer half-lives performed better in the saved bounded grid, but the result should be retested with more seeds and larger windows.

The value of the current work is methodological. The project now has the tools to test lottery strategy ideas responsibly: prize-tier evaluation, confidence intervals, repeated seeds, ablation, match distributions, theoretical baselines, and wider parameter sweeps. Those tools make it easier to distinguish genuine robustness from attractive but fragile historical noise.
