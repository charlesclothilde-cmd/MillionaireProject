# Jackpot Win Pattern Deep Dive

## Abstract

This note starts the next stage of the Millionaire Project: moving from ticket-behaviour analysis to the question of when the EuroMillions jackpot is actually won. The project draw history records dates and winning numbers, but it does not record whether a player won the jackpot. That missing signal matters. A jackpot-winning draw is not a property of the numbers alone; it is a property of the winning numbers plus how many tickets were bought across Europe for that draw.

The new `run_jackpot_analysis.py` script enriches the local draw history with jackpot winner counts from Lottery.co.uk result pages, caches fetched pages, and exports draw-level and summary CSVs. The first run validated the approach but was rate-limited by the source after a small slice of the archive, so the current outputs should be treated as pipeline proof and early sample evidence rather than final conclusions.

## 1. Why This Is Different From Number Analysis

The previous behavioural analysis asked whether a ticket looks human-selected: birthday-heavy numbers, lucky numbers, round numbers, consecutive runs, playslip-like structure, and popular Lucky Stars.

The jackpot-win question is different. For any one EuroMillions ticket, the jackpot odds are fixed at about 1 in 139.8 million. But for a draw as a whole, the chance that someone wins depends on the number of unique combinations played:

```text
P(jackpot won in draw) = 1 - (1 - 1 / 139,838,160) ^ tickets_played
```

This means jackpot wins should be driven mostly by participation and rollover dynamics, not by whether the drawn combination itself looks special after the fact.

## 2. Data Added

The new enrichment script writes:

- `analysis_outputs/jackpot_draw_details.csv`
- `analysis_outputs/jackpot_win_patterns_summary.csv`
- cached HTML pages under `analysis_outputs/jackpot_pages/`

For each draw it attempts to add:

- jackpot prize value;
- UK jackpot winners;
- total jackpot winners;
- whether the jackpot was won;
- winning ticket information when available;
- draw-machine metadata when available;
- timing fields such as year, month, quarter, and weekday;
- simple number-shape fields such as ball sum, odd/even split, low/high split, birthday-number count, consecutive pairs, and star sum.

## 3. First Pipeline Run

The first full run processed the 1,958 local EuroMillions draw dates from 13 February 2004 through 26 June 2026, but Lottery.co.uk returned `403 Forbidden` after the first cacheable slice. The current parsed jackpot-winner coverage is therefore:

```text
Rows in local draw history: 1,958
Rows with parsed jackpot-winner counts: 31
Observed jackpot-winning draws in parsed sample: 8
```

The parsed winning rows are concentrated in early 2004, plus the two latest cached 2026 rows. This sample is not representative enough for final timing conclusions.

## 4. Early Read, With Caveats

In the parsed sample, jackpot-winning rows did not show an obvious drawn-number signature. The average ball sum was almost identical between jackpot-winning and non-winning parsed rows. The birthday-number count and consecutive-pair count differed, but the sample is much too small to treat those as evidence.

This is the expected direction. Whether a jackpot is won should mostly reflect how many tickets were in play. Rollover size, promotional draws, seasonal buying, and country-level participation are more plausible explanatory variables than the final combination's visual shape.

## 5. Analysis Plan Once Coverage Is Complete

The completed deep dive should prioritize these questions:

1. Does jackpot win rate rise with jackpot prize size?
2. Does win rate rise after rollovers, and does it accelerate after very large rollovers?
3. Are Friday and Tuesday draws different after accounting for jackpot size?
4. Are month, quarter, or holiday-period effects visible?
5. Do jackpot-winning combinations have different behavioural signatures, or do apparent differences disappear with more data?
6. Are UK jackpot wins distributed differently from total European jackpot wins?

The most useful model will be a simple logistic comparison:

```text
Jackpot won ~ jackpot size + weekday + month + rollover/proxy + number-shape features
```

The number-shape features should be interpreted as a falsification test. If the model is honest, they should contribute little compared with jackpot size and participation proxies.

## 6. Recommended Next Step

Re-run the enrichment script in small batches after the source rate limit clears:

```bash
python3 run_jackpot_analysis.py --delay 1 --stop-on-forbidden
```

Because pages are cached, each successful run makes permanent progress. Once most rows have parsed jackpot-winner counts, the summary CSV can support a real jackpot-won pattern paper rather than this pipeline note.

## 7. Conclusion

The important conceptual result is already clear: jackpot timing is a participation problem more than a number-pattern problem. The engineering work now exists to test that properly, but the current archive enrichment is incomplete because the source rate-limited bulk fetching. The next reliable conclusion should wait until the draw-level jackpot-winner coverage is high enough to avoid sample bias.
