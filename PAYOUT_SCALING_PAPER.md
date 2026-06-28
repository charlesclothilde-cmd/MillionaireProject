# Payout-Aware Evaluation and Computational Scaling of EuroMillions Backtests

## Abstract

This paper extends the Millionaire Project from match-count evaluation to payout-aware strategy analysis. Earlier work compared EuroMillions ticket-generation strategies by total matches, prize-tier hits, robustness, ablation, and parameter sensitivity. This third paper asks a more practical question: when prize tiers are assigned approximate monetary values, do the strategy rankings change? The project now attaches estimated UK EuroMillions prize values to each backtested ticket, computes gross prize value, net value, return ratio, and return on investment, and exports value-aware summaries for default backtests, repeated-seed runs, ablations, and parameter sweeps. Results remain financially negative for every tested strategy, as expected for a lottery game. However, payout-aware evaluation changes the interpretation of some results: the ranked model produces slightly higher estimated gross value than the random baseline in both the default 200-draw backtest and the repeated-seed robustness run, while the best bounded parameter-grid setting reaches a higher but still negative estimated return. The computational work makes these richer comparisons reproducible through shared schemas, batch outputs, and bounded scalable sweeps, while deeper runtime optimization remains a natural next engineering step.

## 1. Introduction

The first paper introduced the ranked-ticket model and walk-forward backtesting. The second paper stress-tested the model using confidence intervals, repeated seeds, match distributions, model ablation, and parameter sweeps. Those analyses were useful, but they still treated all prize-tier hits mostly as counts.

This paper moves the evaluation closer to practical value. A lottery strategy that produces more low-tier hits is not necessarily better than a strategy that produces fewer hits but occasionally reaches higher-value tiers. A payout-aware analysis therefore asks:

1. how much estimated prize value does each strategy return per ticket;
2. how much does each strategy lose after ticket cost;
3. whether payout-aware ranking differs from match-count or hit-rate ranking;
4. whether the analysis system can support repeated, larger, value-aware experiments.

The answer is deliberately conservative. None of the tested strategies becomes profitable. The value of the work is methodological: the project can now evaluate strategies by estimated return rather than by matches alone.

## 2. Payout Model

The project now defines an approximate UK EuroMillions payout table in `lottery_data.py`. The ticket cost is set to GBP 2.50. Non-jackpot tiers use published expected prizes from the 2020 prize structure, and the jackpot uses a configurable illustrative value of GBP 52,000,000.

| Prize tier | Estimated prize value |
|---|---:|
| 5+2 Jackpot | GBP 52,000,000 |
| 5+1 | GBP 169,001 |
| 5+0 | GBP 17,555 |
| 4+2 | GBP 1,094 |
| 4+1 | GBP 101 |
| 3+2 | GBP 48 |
| 4+0 | GBP 33 |
| 2+2 | GBP 12 |
| 3+1 | GBP 9 |
| 3+0 | GBP 8 |
| 1+2 | GBP 6 |
| 2+1 | GBP 5 |
| 2+0 | GBP 3 |

The project uses these values to compute:

- estimated prize value per ticket;
- estimated net value after ticket cost;
- return ratio;
- return on investment;
- total estimated prize value over a backtest;
- prize-tier contribution by strategy.

The theoretical random expected gross prize value under this payout table is GBP 0.73 per ticket. With a GBP 2.50 ticket cost, the theoretical net expected value is GBP -1.77 and the theoretical ROI is approximately -70.7%.

## 3. Computational Scaling and Reproducibility

The payout-aware work required the analysis pipeline to become more consistent. The project now normalizes all backtest outputs through a shared schema that includes prize tier, estimated prize value, estimated net value, ticket, actual draw, training draw count, and run configuration.

This matters because earlier outputs and newer value-aware outputs need to remain comparable. The `ensure_backtest_schema()` function fills missing derived columns when needed, so summary functions can operate on either fresh backtest results or older saved outputs.

The project also now exports a reproducible batch of analysis files through `run_further_analysis.py`:

- default backtest summary;
- default match distribution;
- default prize-tier value breakdown;
- repeated-seed summary;
- parameter sweep;
- model ablation summary;
- model ablation prize-tier value breakdown;
- theoretical prize probabilities.

The Streamlit app has also been extended so value metrics appear in the Model Lab and Research Lab. These additions make payout-aware analysis part of the normal workflow rather than a separate spreadsheet exercise.

This is computational scaling in the practical research sense: richer outputs, consistent schemas, repeatable batch generation, and bounded parameter sweeps. The core ranked-ticket loop still recomputes model scores for many historical windows, so deeper optimization such as vectorized candidate scoring, score-cache reuse, or incremental weighted-score updates remains future engineering work.

## 4. Methods

### 4.1 Default Payout-Aware Backtest

The default payout-aware backtest uses the same 200-draw walk-forward setup as the first paper:

- minimum training window: 300 draws;
- test window: 200 draws;
- recent draw window: 100 draws;
- ranked-model candidates per draw: 300;
- half-life: 75 draws;
- random seed: 42.

Each generated ticket is compared with the actual draw, assigned a prize tier, assigned an estimated prize value, and summarized by strategy.

### 4.2 Repeated-Seed Value Analysis

The repeated-seed run uses 10 seeds, 75 test draws, 100 ranked candidates per draw, a 300-draw training window, a 100-draw recent window, and a 75-draw half-life. Strategy summaries include mean estimated prize value and value edge versus the random baseline.

### 4.3 Ablation Value Analysis

The ablation test evaluates full and reduced ranked-model variants by estimated prize value as well as matches and hit rate. This checks whether component-level changes affect value, not only total matches.

### 4.4 Parameter Sweep Value Analysis

The bounded parameter grid varies:

- half-life: 25, 75, 150, 250;
- simulations: 100, 300;
- rolling training history: 100, 300;
- recent window: 50, 100;
- test window: 75 draws.

The sweep is sorted by estimated prize value, then prize-hit rate, then average total matches.

## 5. Results

### 5.1 Default Backtest

In the default 200-draw backtest, the ranked model produced the highest estimated prize value among the five strategies.

| Strategy | Draws | Prize hits | Prize-hit rate | Gross value per ticket | Net value per ticket | ROI | Total prize value |
|---|---:|---:|---:|---:|---:|---:|---:|
| Ranked model | 200 | 19 | 9.5% | GBP 0.325 | GBP -2.175 | -87.0% | GBP 65 |
| Random baseline | 200 | 15 | 7.5% | GBP 0.300 | GBP -2.200 | -88.0% | GBP 60 |
| Cold numbers | 200 | 15 | 7.5% | GBP 0.295 | GBP -2.205 | -88.2% | GBP 59 |
| Balanced mix | 200 | 11 | 5.5% | GBP 0.180 | GBP -2.320 | -92.8% | GBP 36 |
| Recent hot | 200 | 8 | 4.0% | GBP 0.175 | GBP -2.325 | -93.0% | GBP 35 |

The ranked model improves slightly over the random baseline in gross value, but the difference is GBP 0.025 per ticket. Both remain strongly negative after ticket cost.

The value breakdown shows that the ranked model's default-run value came only from low prize tiers:

| Prize tier | Ranked-model hits | Total value |
|---|---:|---:|
| 2+0 | 15 | GBP 45 |
| 2+1 | 4 | GBP 20 |

The random baseline generated one 2+2 hit, which is worth more per hit, but fewer total prize-tier hits overall:

| Prize tier | Random-baseline hits | Total value |
|---|---:|---:|
| 2+0 | 11 | GBP 33 |
| 2+1 | 3 | GBP 15 |
| 2+2 | 1 | GBP 12 |

### 5.2 Repeated-Seed Results

In the 10-seed repeated run, the ranked model again led by estimated prize value.

| Strategy | Runs | Mean total matches | Mean prize-hit rate | Mean gross value | Mean net value | Mean ROI | Value edge vs random |
|---|---:|---:|---:|---:|---:|---:|---:|
| Ranked model | 10 | 0.867 | 9.6% | GBP 0.468 | GBP -2.032 | -81.3% | GBP 0.112 |
| Random baseline | 10 | 0.844 | 8.7% | GBP 0.356 | GBP -2.144 | -85.8% | - |
| Balanced mix | 10 | 0.853 | 7.3% | GBP 0.325 | GBP -2.175 | -87.0% | GBP -0.031 |
| Recent hot | 10 | 0.877 | 8.0% | GBP 0.303 | GBP -2.197 | -87.9% | GBP -0.053 |
| Cold numbers | 10 | 0.773 | 6.4% | GBP 0.259 | GBP -2.241 | -89.7% | GBP -0.097 |

This is the clearest payout-aware signal: the ranked model has only a small total-match edge, but a larger value edge than the match-count result alone would suggest. Even so, the mean net value is still approximately GBP -2.03 per GBP 2.50 ticket.

### 5.3 Ablation Results

The payout-aware ablation results match the earlier hit-rate interpretation: removing spread helped in the short ablation window, while removing hot score hurt.

| Variant | Draws | Gross value per ticket | Net value per ticket | ROI | Prize-hit rate | Total prize value |
|---|---:|---:|---:|---:|---:|---:|
| No spread score | 50 | GBP 0.720 | GBP -1.780 | -71.2% | 14.0% | GBP 36 |
| Full model | 50 | GBP 0.660 | GBP -1.840 | -73.6% | 12.0% | GBP 33 |
| No balance score | 50 | GBP 0.580 | GBP -1.920 | -76.8% | 12.0% | GBP 29 |
| No cold score | 50 | GBP 0.560 | GBP -1.940 | -77.6% | 10.0% | GBP 28 |
| Only hot score | 50 | GBP 0.520 | GBP -1.980 | -79.2% | 10.0% | GBP 26 |
| No pair score | 50 | GBP 0.400 | GBP -2.100 | -84.0% | 6.0% | GBP 20 |
| No hot score | 50 | GBP 0.300 | GBP -2.200 | -88.0% | 4.0% | GBP 15 |
| Only pair score | 50 | GBP 0.160 | GBP -2.340 | -93.6% | 4.0% | GBP 8 |
| Only balance/spread | 50 | GBP 0.000 | GBP -2.500 | -100.0% | 0.0% | GBP 0 |

This supports the same modelling hypothesis as the second paper: hot-score information appears useful, and the spread component may be too restrictive in the tested window.

### 5.4 Parameter Sweep Results

The top saved parameter-grid cell used:

- half-life: 250 draws;
- simulations: 100;
- rolling training history: 300 draws;
- recent window: 50 or 100 draws;
- test window: 75 draws.

It achieved:

- average total matches: 1.053;
- prize-hit rate: 16.0%;
- gross value per ticket: GBP 0.773;
- net value per ticket: GBP -1.727;
- return ratio: 30.9%;
- ROI: -69.1%;
- best prize tier: 2+2.

This is better than the default ranked model in the saved analyses, but it still loses money under the approximate payout table. The result is best understood as a parameter-search finding that deserves larger repeated validation.

## 6. Discussion

Payout-aware evaluation changes the tone of the analysis. A model can look acceptable by hit rate while still producing poor value if its hits are concentrated in the lowest tiers. Conversely, a strategy with fewer hits can appear better if it reaches higher-value tiers. The current ranked model's value advantage is modest and mostly driven by more low-tier hits, not by reaching high prize tiers.

The comparison with theoretical expected return is also important. Under the illustrative payout table, the theoretical random gross EV is GBP 0.73 per ticket, but the observed 200-draw random baseline produced GBP 0.30 per ticket. This gap is not surprising in a finite historical sample where rare high-value tiers are usually absent. It is a reminder that short backtests can severely underrepresent the tail of lottery payouts.

The ranked model's repeated-seed value result is directionally encouraging because it beats the simulated random baseline on mean estimated value. But this should not be confused with positive expected value. The mean ranked-model ROI remains around -81.3% in that repeated run.

The computational changes make these comparisons easier to reproduce. The project now has a shared result schema, value-aware summaries, prize-tier value tables, theoretical EV outputs, and batch-generated CSVs. This is enough to support practical research iteration. The remaining performance bottleneck is the ranked candidate-generation loop, which still recomputes weighted number and pair scores across many historical windows.

## 7. Limitations

The payout values are approximate. Non-jackpot prizes vary by draw, country, exchange context, and prize pool. The jackpot value is illustrative and configurable. Therefore, the monetary results should be read as estimated value under a fixed payout table, not as exact historical returns.

The observed backtests are too short to estimate jackpot-driven expected value. Rare high-value outcomes dominate theoretical lottery EV, but they almost never appear in historical strategy replay at this scale. For that reason, the practical reported returns are mostly driven by low-tier prizes.

The computational scaling work improves reproducibility and workflow breadth, but it is not a final high-performance engine. Larger seed counts, larger candidate pools, and full historical grids will benefit from future optimization.

## 8. Conclusion

The third stage of the Millionaire Project adds payout-aware evaluation and a more scalable analysis workflow. The ranked model remains slightly stronger than the random baseline in the saved value-aware summaries, especially in repeated-seed testing, but every tested strategy remains negative after ticket cost.

The main contribution is not a profitable lottery method. It is a better evaluation framework. The project can now ask whether a strategy produces more value, not merely more matches, and it can reproduce that question across default backtests, repeated seeds, ablations, and parameter sweeps. That makes future modelling work more honest, because any claimed improvement must survive both statistical and payout-aware scrutiny.

