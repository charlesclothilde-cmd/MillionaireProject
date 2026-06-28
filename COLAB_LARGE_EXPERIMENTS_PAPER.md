# Large-Scale Colab Experiments and Repeated Ablation in the Millionaire Project

## Abstract

This paper documents the fourth stage of the Millionaire Project: scaling payout-aware EuroMillions strategy experiments in Google Colab and using larger repeated runs to test whether earlier model signals survive more compute. Prior work added ranked-ticket modelling, walk-forward backtesting, robustness checks, prize-tier evaluation, and approximate GBP payout values. The Colab experiments extend that work with a 100-seed repeated strategy comparison, a single-seed parameter sweep, a 200-draw ablation retest, and a 50-seed repeated ablation study. Results remain negative after ticket cost for every strategy, but the larger experiments clarify the model story. The ranked model shows a small median value edge over the random baseline in the 100-seed run. The most important new finding is component-level: across 50 repeated ablation seeds, removing the balance score produced the highest median expected prize value, suggesting that the current balance heuristic may over-constrain the ranked model for payout-aware outcomes.

## 1. Introduction

The Millionaire Project has deliberately treated lottery modelling as an exercise in disciplined comparison rather than prediction. EuroMillions draws are designed to be random, so the project does not try to prove that future outcomes can be forecast. Instead, it asks whether different ticket-construction rules behave differently when replayed through historical draws without look-ahead bias.

Earlier papers established:

1. a ranked model using recency-weighted frequency, pair history, balance, spread, and cold-number exposure;
2. walk-forward backtests against simple baselines;
3. prize-tier, confidence-interval, repeated-seed, ablation, and parameter-sensitivity analysis;
4. payout-aware evaluation using approximate UK EuroMillions prize values.

The latest question is computational and methodological: what changes when the experiments are large enough to reduce seed noise, and when payout-aware summaries use medians as well as means?

Google Colab was used as a practical scaling environment. This made it possible to run larger repeated experiments without relying on a slow local machine, while keeping the notebook and outputs reproducible through GitHub and Google Drive.

## 2. Methods

### 2.1 Colab Notebook Workflow

The large-experiment workflow is stored in `large_experiments_colab.ipynb`. The notebook:

- clones the GitHub repository into Colab;
- installs dependencies from `requirements.txt`;
- loads `euromillions_full_2004_2026.csv`;
- runs a small smoke test to verify the environment;
- runs larger repeated-seed and parameter experiments;
- saves CSV outputs to Google Drive;
- records result tables directly in the notebook.

The smoke test is intentionally small. It is used only to verify setup, not to draw modelling conclusions.

### 2.2 Payout-Aware Metrics

The experiments reuse the approximate payout model introduced in the payout-scaling paper. Each ticket receives:

- prize tier;
- estimated gross prize value;
- estimated net value after the GBP 2.50 ticket cost;
- return ratio;
- ROI.

Because rare prize tiers can dominate mean value, the Colab analysis also emphasizes median expected prize value and median ROI. This is especially important in lottery analysis, where one rare high-tier hit can make an otherwise weak strategy appear profitable in the mean.

### 2.3 Repeated Strategy Comparison

The main repeated strategy comparison used:

- 100 seeds;
- 200 test draws;
- 300-draw training window;
- 100 ranked candidates per tested draw;
- 250-draw recency half-life;
- 100-draw recent window for strategies that use a recent-window parameter.

The strategies were:

- Random baseline;
- Recent hot;
- Cold numbers;
- Balanced mix;
- Ranked model.

### 2.4 Parameter Sweep

The parameter sweep varied:

- half-life: 75, 150, 250, 400;
- simulations: 100, 300;
- training window: 300, 500;
- recent window: 50, 100;
- test window: 200 draws.

This sweep used one random seed. It is therefore treated as hypothesis generation rather than robust evidence.

### 2.5 Repeated Ablation

The repeated ablation study used:

- 50 seeds;
- 200 test draws;
- 300-draw training window;
- 300-draw history window;
- 300 simulations per tested draw;
- 250-draw half-life.

It compared the full ranked model with component-removal and component-isolation variants:

- Full model;
- No hot score;
- No cold score;
- No balance score;
- No spread score;
- No pair score;
- Only hot score;
- Only pair score;
- Only balance/spread.

## 3. Results

### 3.1 Smoke Test

The smoke test ran successfully. It produced plausible result columns for all strategies and confirmed that the Colab runtime could import project code, load the data, execute repeated backtests, compute payout-aware summaries, and display tables.

The smoke test used only 3 seeds and 25 test draws. Its results are not used as modelling evidence.

### 3.2 100-Seed Strategy Comparison

The 100-seed run showed a small median advantage for the ranked model over the random baseline.

| Strategy | Median total matches | Median prize-hit rate | Median expected prize value | Median ROI |
|---|---:|---:|---:|---:|
| Ranked model | 0.830 | 7.5% | GBP 0.3275 | -86.9% |
| Balanced mix | 0.825 | 7.5% | GBP 0.3175 | -87.3% |
| Random baseline | 0.830 | 7.5% | GBP 0.3150 | -87.4% |
| Cold numbers | 0.805 | 8.0% | GBP 0.3125 | -87.5% |
| Recent hot | 0.815 | 7.5% | GBP 0.3100 | -87.6% |

The mean table initially ranked Cold numbers first by expected value because one seed hit a rare high-value tier. The outlier row reached an expected prize value of GBP 845.365 per ticket for that seed. This demonstrates why mean payout value alone is fragile in lottery experiments.

The median result is more stable. Under that view, the ranked model leads, but only modestly:

```text
Ranked model median EV: GBP 0.3275
Random baseline median EV: GBP 0.3150
Median edge: GBP 0.0125 per ticket
```

This is a small edge and remains strongly negative after ticket cost.

### 3.3 Parameter Sweep

The best single-seed parameter-sweep cell used:

- half-life: 250;
- simulations: 100;
- training window: 300;
- test draws: 200;
- recent window: 50 or 100.

It achieved:

- average total matches: 0.955;
- prize-hit rate: 13.5%;
- expected prize value: GBP 0.620;
- ROI: -75.2%;
- best prize tier: 2+2.

The duplicate results for recent-window values of 50 and 100 confirm an implementation detail: the ranked model does not currently use recent-window directly. That parameter affects the simpler recent-hot and balanced-mix strategies, but the ranked score uses recency through the half-life parameter.

The strongest parameter-sweep lesson is not that this cell is proven best. It is that `half_life=250`, `simulations=100`, and `training_window=300` deserve repeated-seed validation. When the leading configuration was checked in the 100-seed repeated run, its mean expected value was much closer to GBP 0.331 per ticket, so the single-seed sweep result likely contained seed/window luck.

### 3.4 Single-Seed Ablation Retest

The single-seed 200-draw ablation retest changed the earlier short-window interpretation. In the previous shorter analysis, removing the spread score looked strongest. In the larger 200-draw retest, removing spread fell near the bottom, while removing balance produced the highest expected prize value.

This contradiction was useful. It showed that single-seed ablations are not stable enough to choose a model component. A repeated ablation was needed.

### 3.5 50-Seed Repeated Ablation

The 50-seed repeated ablation is the strongest new result in this stage. Removing the balance score produced the highest median expected prize value.

| Variant | Runs | Median total matches | Mean total matches | Median prize-hit rate | Mean prize-hit rate | Median expected prize value | Mean expected prize value | Median ROI | Mean ROI |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| No balance score | 50 | 0.8375 | 0.8288 | 8.25% | 8.44% | GBP 0.3825 | GBP 0.3719 | -84.7% | -85.1% |
| Only balance/spread | 50 | 0.8550 | 0.8511 | 8.00% | 8.10% | GBP 0.3550 | GBP 0.3678 | -85.8% | -85.3% |
| No cold score | 50 | 0.8200 | 0.8224 | 8.00% | 7.87% | GBP 0.3475 | GBP 0.3559 | -86.1% | -85.8% |
| Full model | 50 | 0.8250 | 0.8277 | 8.00% | 7.90% | GBP 0.3400 | GBP 0.3514 | -86.4% | -85.9% |
| No pair score | 50 | 0.8300 | 0.8282 | 8.00% | 7.92% | GBP 0.3400 | GBP 0.3445 | -86.4% | -86.2% |
| Only hot score | 50 | 0.8100 | 0.8114 | 8.00% | 7.68% | GBP 0.3300 | GBP 0.3424 | -86.8% | -86.3% |
| No hot score | 50 | 0.8300 | 0.8200 | 8.00% | 7.66% | GBP 0.3250 | GBP 0.4264 | -87.0% | -82.9% |
| No spread score | 50 | 0.8025 | 0.8026 | 7.00% | 7.10% | GBP 0.2925 | GBP 0.3047 | -88.3% | -87.8% |
| Only pair score | 50 | 0.8225 | 0.8200 | 7.00% | 7.62% | GBP 0.2925 | GBP 0.3138 | -88.3% | -87.4% |

The median expected value edge versus the full model is:

```text
No balance score median EV: GBP 0.3825
Full model median EV: GBP 0.3400
Median edge: GBP 0.0425 per ticket
```

That is meaningful within the project's modelling context, though still not financially positive.

## 4. Discussion

The Colab experiments refine the model story in three ways.

First, the ranked model remains mildly competitive with random under repeated payout-aware evaluation. Its median expected value leads the random baseline in the 100-seed run, but the edge is small. This supports the cautious conclusion from earlier papers: the model may shape tickets differently from chance, but the effect is close to noise and nowhere near positive expected value.

Second, mean payout value can be actively misleading. The Cold numbers strategy appeared spectacular by mean expected value in the 100-seed run because of one rare high-value outcome. The median table told a much calmer story. Future project summaries should report medians alongside means whenever payout metrics are involved.

Third, the repeated ablation points to a concrete model change. The balance score appears to reduce payout-aware value when used inside the full ranked model. This does not mean that ticket balance is useless. The Only balance/spread variant had the best median total matches. Instead, the result suggests that the current balance implementation or weight may over-constrain candidate selection when combined with hot, cold, spread, and pair features.

The spread result also changed. Earlier short-window ablation suggested that removing spread might help. The 50-seed repeated ablation does not support that idea. No spread score was near the bottom by median expected value.

## 5. Recommended Next Experiments

The next candidate model should be a ranked model without the balance component. It should not immediately replace the default model. First, it should be tested in a direct head-to-head experiment against:

- Full model;
- No balance score;
- No cold score;
- Only balance/spread;
- Random baseline.

The head-to-head should use at least:

- 100 seeds;
- 200 test draws;
- half-life 250;
- 100 and 300 simulation settings;
- median expected value, median ROI, win rate versus random, and outlier diagnostics.

The project should also add median payout metrics to official summary functions and Streamlit views. The current mean payout summaries are useful, but the Colab results show that medians are necessary for stable interpretation.

## 6. Limitations

These experiments still do not prove a predictive lottery edge. EuroMillions draws are random by design, and historical replay cannot establish future predictability.

The payout table is approximate. Non-jackpot prizes vary by draw, and the jackpot value is illustrative. Payout-aware results are therefore modelled values under a fixed prize table, not exact historical returns.

The repeated ablation uses 50 seeds, which is better than a single seed but still finite. Rare payout events can still affect means. Medians reduce this problem but do not remove all uncertainty.

Colab scaling improves practical compute access, but the ranked-ticket loop remains computationally expensive. Larger sweeps would benefit from score caching, vectorized candidate scoring, and incremental updates to weighted number and pair scores.

## 7. Conclusion

The Colab experiments strengthen the Millionaire Project's research workflow. They show how to move from local exploratory runs to larger, reproducible repeated experiments, and they expose why payout-aware lottery analysis must use robust summaries.

The ranked model remains only modestly better than random by median value in the 100-seed strategy comparison. The stronger contribution is the repeated ablation result: removing the balance score produced the best median payout-aware outcome across 50 seeds.

The project should treat `No balance score` as the leading candidate for the next ranked-model variant. Even so, all tested strategies remain negative after ticket cost. The value of the work is methodological: better experiments, clearer model diagnostics, and more honest interpretation of noisy payout-driven results.
