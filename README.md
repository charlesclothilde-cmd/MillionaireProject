# Millionaire Project

EuroMillions strategy analysis and backtesting lab.

This project explores lottery-ticket generation strategies with historical EuroMillions data. It includes a Streamlit app, a ranked ticket model, walk-forward backtests, robustness checks, and short research write-ups. The goal is not to predict the lottery. EuroMillions draws are designed to be random; this project is an exploratory tool for testing whether different ticket-construction rules behave differently under historical replay.

## What It Does

- Generates valid EuroMillions tickets from several strategies:
  - recent hot numbers
  - cold numbers
  - clustered historical draws
  - balanced hot/cold mixes
  - ranked Monte Carlo candidates
- Scores ranked tickets using recency-weighted frequency, historical pair frequency, ticket balance, spread, and cold-number exposure.
- Runs walk-forward backtests that only use draws available before each tested date.
- Compares strategies against a random baseline.
- Reports prize-tier hits, confidence intervals, match distributions, repeated-seed robustness, ablations, and parameter sweeps.

## Run The App

Install the Python dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Start Streamlit:

```bash
streamlit run streamlit_app.py
```

The app opens with three tabs:

- **Ticket generator**: generate tickets from simple historical strategies.
- **Model Lab**: inspect ranked tickets and run walk-forward backtests.
- **Research Lab**: run repeated-seed checks, ablations, and parameter sweeps.

## Data

The main dataset is:

```text
euromillions_full_2004_2026.csv
```

It contains draw dates, five main balls, and two Lucky Stars. Data loading and validation live in `lottery_data.py`.

The scraper in `scrape_euromillions.py` fetches historical archive pages from:

```text
https://www.lottery.co.uk/euromillions/results/archive-YYYY
```

See `DATA_UPDATE.md` for the update workflow.

## Research Notes

Three write-ups document the modelling work:

- `MODEL_BACKTESTING_PAPER.md`: first ranked-model and walk-forward backtesting analysis.
- `FURTHER_ANALYSIS_PAPER.md`: robustness, ablation, prize-tier, and parameter-sensitivity analysis.
- `PAYOUT_SCALING_PAPER.md`: payout-aware expected value analysis and scalable experiment outputs.

The headline result is deliberately modest: some model configurations are competitive with simple baselines in selected windows, but effects are small, unstable, and close to mathematical random expectations.

## Tests

Run the test suite with:

```bash
python3 -m unittest
```

The current tests cover draw validation, prize-tier scoring, theoretical expected matches, and a no-look-ahead property for backtesting.

## Project Structure

```text
streamlit_app.py              Streamlit user interface
lottery_data.py               Data loading, validation, ticket generation, scoring, backtesting
scrape_euromillions.py        Archive scraper for historical draw data
update_results.py             Append validated new draws to the master CSV
run_further_analysis.py       Batch generation of robustness outputs
tests/                        Unit tests
analysis_outputs/             Generated analysis summaries and backtest outputs
```

## Important Disclaimer

This project is for analysis and experimentation only. It does not provide financial advice, gambling advice, or a reliable way to predict lottery results. Treat generated tickets as entertainment, not as evidence of an edge.

## License

Code is released under the MIT License. Lottery draw data remains factual source data; check source-site terms before redistributing scraped data elsewhere.
