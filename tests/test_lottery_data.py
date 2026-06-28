from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lottery_data import (  # noqa: E402
    NO_PRIZE_TIER,
    backtest_strategies,
    normalize_draws,
    prize_tier,
    score_match,
    theoretical_expected_matches,
)


class LotteryDataTests(unittest.TestCase):
    def test_validate_draws_rejects_duplicate_balls(self):
        raw = pd.DataFrame(
            [
                {
                    "Date": "2026-01-02",
                    "Year": 2026,
                    "Balls": "[1, 1, 2, 3, 4]",
                    "LuckyStars": "[1, 2]",
                }
            ]
        )

        with self.assertRaisesRegex(ValueError, "duplicates"):
            normalize_draws(raw)

    def test_validate_draws_rejects_duplicate_dates(self):
        raw = pd.DataFrame(
            [
                {"Date": "2026-01-02", "Year": 2026, "Balls": "[1, 2, 3, 4, 5]", "LuckyStars": "[1, 2]"},
                {"Date": "2026-01-02", "Year": 2026, "Balls": "[6, 7, 8, 9, 10]", "LuckyStars": "[3, 4]"},
            ]
        )

        with self.assertRaisesRegex(ValueError, "Duplicate draw dates"):
            normalize_draws(raw)

    def test_prize_tier_scoring(self):
        ticket = ([1, 2, 3, 4, 5], [1, 2])
        jackpot_draw = ([1, 2, 3, 4, 5], [1, 2])
        small_prize_draw = ([1, 2, 10, 11, 12], [3, 4])
        no_prize_draw = ([1, 10, 11, 12, 13], [3, 4])

        self.assertEqual(score_match(ticket, jackpot_draw), (5, 2))
        self.assertEqual(prize_tier(*score_match(ticket, jackpot_draw)), "5+2 Jackpot")
        self.assertEqual(prize_tier(*score_match(ticket, small_prize_draw)), "2+0")
        self.assertEqual(prize_tier(*score_match(ticket, no_prize_draw)), NO_PRIZE_TIER)

    def test_theoretical_expected_matches(self):
        expected = theoretical_expected_matches()

        self.assertAlmostEqual(expected["ball_matches"], 0.5)
        self.assertAlmostEqual(expected["star_matches"], 1 / 3)
        self.assertAlmostEqual(expected["total_matches"], 5 / 6)

    def test_backtest_uses_only_prior_draws(self):
        raw = pd.DataFrame(
            [
                {"Date": "2026-01-02", "Year": 2026, "Balls": "[1, 2, 3, 4, 5]", "LuckyStars": "[1, 2]"},
                {"Date": "2026-01-09", "Year": 2026, "Balls": "[6, 7, 8, 9, 10]", "LuckyStars": "[3, 4]"},
                {"Date": "2026-01-16", "Year": 2026, "Balls": "[11, 12, 13, 14, 15]", "LuckyStars": "[5, 6]"},
                {"Date": "2026-01-23", "Year": 2026, "Balls": "[16, 17, 18, 19, 20]", "LuckyStars": "[7, 8]"},
                {"Date": "2026-01-30", "Year": 2026, "Balls": "[21, 22, 23, 24, 25]", "LuckyStars": "[9, 10]"},
                {"Date": "2026-02-06", "Year": 2026, "Balls": "[26, 27, 28, 29, 30]", "LuckyStars": "[11, 12]"},
            ]
        )
        draws = normalize_draws(raw)

        results = backtest_strategies(draws, training_window=3, test_draws=2, simulations=5, random_seed=7)

        self.assertFalse(results.empty)
        self.assertTrue((results["Training through"] < results["Date"]).all())
        self.assertEqual(sorted(results["Training draws"].unique().tolist()), [4, 5])


if __name__ == "__main__":
    unittest.main()
