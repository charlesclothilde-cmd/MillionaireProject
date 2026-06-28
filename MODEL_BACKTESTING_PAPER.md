# From Backtesting to Modelling in the Millionaire Project

## Abstract

This paper documents the recent addition of a Model Lab to the Millionaire Project, a EuroMillions analysis application built around historical draw data. The addition extends the original ticket generator with a ranked ticket model and a walk-forward backtesting framework. The ranked model scores Monte Carlo candidate tickets using recency-weighted number frequency, historical pair frequency, ticket balance, numerical spread, and a small counterweight for cold numbers. The backtest compares this model with simpler strategies using only information available before each tested draw. Results on a draw history of 1,958 EuroMillions draws from 13 February 2004 through 26 June 2026 show that the ranked model is competitive with the random baseline and leads over a 500-draw test window, but its advantage is small and unstable. The evidence supports the Model Lab as a disciplined strategy-comparison tool, not as proof that lottery outcomes are predictable.

## 1. Introduction

The Millionaire Project began as a practical lottery exploration tool: load EuroMillions history, identify common numbers, cluster historical draws, and generate candidate tickets. The recent addition moves the project from descriptive analysis toward model evaluation. It adds two linked capabilities:

1. a ranked ticket model that scores candidate tickets before selection;
2. a walk-forward backtest that evaluates each strategy on future draws only.

This change is important methodologically. Frequency tables and clustering can make an application feel analytical, but without a backtest they do not show whether a method performs differently from chance. The new Model Lab therefore asks a sharper question: if the strategy had been run historically using only the data available at that time, how many numbers would it have matched?

## 2. Data

The project uses `euromillions_full_2004_2026.csv` as its master draw file. The current dataset includes real draw dates through 26 June 2026. The data contains 1,958 rows covering draws from 13 February 2004 to 26 June 2026. Each row stores:

- `Date`: the actual draw date;
- `Year`: the draw year;
- `Balls`: five main numbers from 1 to 50;
- `LuckyStars`: two star numbers from 1 to 12.

Data quality checks in `lottery_data.py` validate that each draw has exactly five unique balls and two unique Lucky Stars, all within the legal EuroMillions ranges. Duplicate dated draws are rejected.

## 3. Recent Addition: Model Lab

The new Model Lab appears in `streamlit_app.py` as a second Streamlit tab beside the original ticket generator. It exposes two workflows.

The first workflow is the ranked ticket model. A user chooses the number of Monte Carlo candidates, a recency half-life, and the number of ranked tickets to display. The application then generates random valid tickets, scores them, sorts them, and displays the best candidates with component scores.

The second workflow is the walk-forward backtest. A user chooses the number of test draws, the minimum training window, and the candidate count per draw. The application then compares five strategies:

- Random baseline;
- Recent hot numbers;
- Cold numbers;
- Balanced mix;
- Ranked model.

The central improvement is the separation between training history and evaluation draw. For each test date, the strategy is built from earlier draws only, then evaluated against the next actual draw.

## 4. Methodology

### 4.1 Ticket Generation Strategies

The random baseline samples five balls from 1-50 and two Lucky Stars from 1-12. This is the benchmark any lottery strategy must be compared against.

The recent-hot strategy counts the most frequent numbers in a recent draw window, then samples from the top candidates.

The cold-number strategy identifies historically least frequent numbers and samples from that pool.

The balanced-mix strategy combines recent hot numbers with long-run cold numbers. It uses the recent window for short-term frequency and the full history for underrepresented numbers.

The ranked model generates many random candidate tickets and assigns each a score. It returns the highest-scoring candidates.

### 4.2 Ranked Model Score

The ranked model uses five components:

- hot score;
- cold score;
- balance score;
- spread score;
- pair score.

Hot and pair scores are recency-weighted. A half-life parameter controls how quickly older draws lose influence. In the default configuration, the half-life is 75 draws, so a draw 75 positions older contributes half as much as the newest draw.

The hot score rewards numbers that have appeared often in the recency-weighted history. Balls contribute 75% of the hot score and Lucky Stars contribute 25%.

The cold score is the complement of the hot score. It gives the model a modest preference for numbers that are not already dominant in the weighted history.

The balance score rewards tickets with a reasonable odd/even split, low/high split, and total-ball sum near the middle of the possible range. This is a structural feature: it does not claim that balanced tickets are more likely, only that it discourages extreme combinations.

The spread score rewards a main-ball range near 36, encouraging tickets that are neither tightly clustered nor maximally dispersed.

The pair score measures how often pairs of main balls have appeared together in the recency-weighted historical data.

The final score is a weighted sum:

```text
score =
  0.34 * hot_score
+ 0.16 * cold_score
+ 0.24 * balance_score
+ 0.11 * spread_score
+ 0.15 * pair_score
```

These weights are heuristic. They encode a modelling preference for recency and ticket shape, but they are not learned from a separate optimization process.

### 4.3 Walk-Forward Backtesting

The backtest sorts all dated draws chronologically. For each tested draw:

1. all earlier draws become the training history;
2. each strategy generates one ticket from that history;
3. the ticket is compared with the actual draw;
4. ball matches, star matches, and total matches are recorded.

This design avoids look-ahead bias. No tested strategy can use the draw it is being evaluated against.

The default app backtest uses:

- minimum training window: 300 draws;
- test window: 200 draws;
- recent draw window: 100 draws;
- ranked-model candidates per draw: 300;
- recency half-life: 75 draws;
- random seed: 42.

Additional robustness checks were run with a 500-draw test window and alternative half-lives of 25 and 250 draws.

## 5. Results

### 5.1 Default 200-Draw Backtest

The default backtest covers the latest 200 available draws. Average matches per ticket were:

| Strategy | Draws | Avg ball matches | Avg star matches | Avg total matches | Best total matches | Three-plus match rate |
|---|---:|---:|---:|---:|---:|---:|
| Random baseline | 200 | 0.515 | 0.320 | 0.835 | 4 | 2.0% |
| Ranked model | 200 | 0.495 | 0.325 | 0.820 | 3 | 2.0% |
| Balanced mix | 200 | 0.460 | 0.335 | 0.795 | 3 | 0.5% |
| Recent hot | 200 | 0.440 | 0.330 | 0.770 | 3 | 2.0% |
| Cold numbers | 200 | 0.475 | 0.285 | 0.760 | 3 | 2.5% |

In this window, the random baseline narrowly led the ranked model. This is not surprising: the theoretical expected total matches for a random EuroMillions ticket is approximately 0.833, which is almost identical to the observed random-baseline average of 0.835.

### 5.2 Longer 500-Draw Backtest

The 500-draw test gives a broader view:

| Strategy | Draws | Avg ball matches | Avg star matches | Avg total matches | Best total matches | Three-plus match rate |
|---|---:|---:|---:|---:|---:|---:|
| Ranked model | 500 | 0.542 | 0.382 | 0.924 | 3 | 3.4% |
| Random baseline | 500 | 0.532 | 0.342 | 0.874 | 4 | 3.8% |
| Balanced mix | 500 | 0.542 | 0.330 | 0.872 | 3 | 3.0% |
| Cold numbers | 500 | 0.500 | 0.328 | 0.828 | 4 | 3.2% |
| Recent hot | 500 | 0.500 | 0.318 | 0.818 | 4 | 3.2% |

Over 500 draws, the ranked model produced the highest average total matches, mainly through stronger Lucky Star matching. However, its best total match was lower than the random baseline's best total match, and the three-plus match rate was slightly lower than random. This indicates that the model improved average matching in this sample without clearly dominating the baseline across all outcome measures.

### 5.3 Half-Life Sensitivity

The half-life setting affects how aggressively the model favors recent draws. In the 200-draw test:

| Half-life | Ranked-model avg ball matches | Ranked-model avg star matches | Ranked-model avg total matches |
|---:|---:|---:|---:|
| 25 | 0.485 | 0.310 | 0.795 |
| 75 | 0.495 | 0.325 | 0.820 |
| 250 | 0.460 | 0.375 | 0.835 |

Longer memory improved star matching in this specific window, while shorter memory reduced total performance. Even so, all results remained close to the random expectation.

### 5.4 Example Ranked Tickets

Using the full dataset, 1,000 Monte Carlo candidates, and a 75-draw half-life, the top ranked tickets were:

| Rank | Balls | Lucky Stars | Score |
|---:|---|---|---:|
| 1 | 4, 14, 17, 31, 41 | 2, 8 | 0.648 |
| 2 | 6, 13, 29, 39, 42 | 4, 7 | 0.648 |
| 3 | 6, 16, 17, 28, 41 | 9, 10 | 0.648 |
| 4 | 13, 14, 18, 31, 48 | 10, 12 | 0.647 |
| 5 | 6, 13, 17, 36, 41 | 3, 5 | 0.646 |

These tickets should be read as model-preferred candidates, not as predictions.

## 6. Discussion

The Model Lab improves the project in two ways. First, it formalizes ticket scoring, making the generator more transparent. A user can see whether a suggested ticket is driven by recency, balance, spread, or historical pair behavior. Second, it introduces an honest evaluation loop. Strategies are no longer judged by whether they sound plausible; they are judged by how they performed on held-out future draws.

The results are deliberately modest. In the 200-draw default backtest, the ranked model did not beat the random baseline. In the 500-draw backtest, it did beat the baseline by 0.050 total matches per draw, but this is a small effect in a noisy domain. The half-life sensitivity check also shows that parameter choices can alter the result. This makes the model useful for experimentation, but not for claims of reliable predictive power.

The core limitation is the lottery process itself. EuroMillions draws are designed to be random. Historical frequency, recency, and co-occurrence patterns may create interesting descriptive structure, but they should not be expected to create a durable forecasting edge. The proper interpretation is therefore comparative and exploratory: the model tests whether different ticket-construction rules behave differently under historical replay.

## 7. Conclusion

The recent addition of ranked modelling and walk-forward backtesting turns the Millionaire Project from a descriptive generator into an evaluable modelling tool. The ranked model combines recency-weighted frequency, cold-number exposure, ticket balance, spread, and pair history into a single score, then tests its selections against future draws without look-ahead bias.

Empirically, the model is competitive and occasionally stronger than simpler strategies, especially in the 500-draw backtest. However, its gains are small, sensitive to settings, and close to the random baseline. The best conclusion is that the Model Lab adds methodological discipline: it helps compare strategies responsibly while preserving the essential warning that lottery tickets remain games of chance.

## 8. Future Work

The first round of results motivates a second, more focused analysis of robustness. That companion paper extends the work here with prize-tier evaluation, confidence intervals, repeated-seed tests, model ablation, match-distribution analysis, theoretical prize odds, and a wider parameter grid. The purpose of that follow-up is not to claim predictive certainty, but to test whether the ranked model's small apparent advantages survive more careful stress-testing.

The main open questions are whether any scoring component contributes durable signal, whether the apparent gains are stable across random seeds and rolling training windows, and whether performance changes meaningfully when evaluation shifts from total matches to prize-tier outcomes.
