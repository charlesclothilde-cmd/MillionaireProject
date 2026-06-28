# EuroMillions Data Update Process

This project uses `euromillions_full_2004_2026.csv` as the master draw history
for the Streamlit app. The CSV now stores real draw dates, so you do not need to
manually add new rows by hand.

## What The Scraper Does

`scrape_euromillions.py` fetches yearly EuroMillions archive pages from:

```text
https://www.lottery.co.uk/euromillions/results/archive-YYYY
```

For each year, it extracts:

- the actual draw date
- the five main balls
- the two Lucky Stars

It then normalizes the data into this project format:

```csv
Date,Year,Balls,LuckyStars
2004-02-13,2004,"[16, 29, 32, 36, 41]","[7, 9]"
```

Before writing the CSV, the scraper validates that every draw has exactly five
unique balls between 1 and 50, and two unique Lucky Stars between 1 and 12.

## Update The Master CSV

Run this from the project folder:

```bash
/Users/clothilde/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scrape_euromillions.py
```

By default, this fetches all years from 2004 through the current year and writes:

```text
euromillions_full_2004_2026.csv
```

The Streamlit app already reads that file, so after the command finishes the app
will automatically use the updated draw history.

## Test Without Changing The CSV

Use `--dry-run` when you want to check the scraper without overwriting anything:

```bash
/Users/clothilde/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scrape_euromillions.py --dry-run
```

You can also test one year:

```bash
/Users/clothilde/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scrape_euromillions.py --start-year 2024 --end-year 2024 --dry-run
```

## Useful Options

- `--start-year 2004`: first archive year to fetch
- `--end-year 2026`: last archive year to fetch
- `--output some_file.csv`: write to another CSV instead of the master file
- `--dry-run`: fetch and validate only, without writing
- `--delay 0.25`: pause between year requests so the source site is not hit too fast

## Backup

The previous master CSV was saved as:

```text
euromillions_full_2004_2024.csv.bak
```

Keep it if you want an easy rollback point.

## How It Connects To The App

`streamlit_app.py` calls `load_draws()` from `lottery_data.py`.

`load_draws()` reads `euromillions_full_2004_2026.csv`, parses `Date`, `Balls`,
and `LuckyStars`, and validates the rows. The app freshness caption uses the
latest date in the CSV, so once the scraper runs successfully you should see a
message like:

```text
Dataset updated through 2026-06-26
```
