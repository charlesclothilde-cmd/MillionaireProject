from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lottery_data import (  # noqa: E402
    NO_PRIZE_TIER,
    TICKET_COST_GBP,
    analyse_ticket_behavior,
    backtest_strategies,
    estimated_prize_value,
    generate_anti_crowd_tickets,
    normalize_draws,
    prize_value_table,
    prize_tier,
    score_match,
    summarise_backtest,
    summarise_prize_tier_values,
    theoretical_expected_matches,
    theoretical_expected_return,
    theoretical_prize_probabilities,
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

    def test_prize_values_and_theoretical_expected_return(self):
        self.assertGreater(estimated_prize_value("5+2 Jackpot"), estimated_prize_value("5+1"))
        self.assertEqual(estimated_prize_value(NO_PRIZE_TIER), 0.0)

        table = prize_value_table()
        self.assertIn("Estimated prize value", table.columns)
        self.assertIn("Source note", table.columns)

        odds = theoretical_prize_probabilities()
        self.assertIn("Expected value contribution", odds.columns)
        self.assertGreater(float(odds["Expected value contribution"].sum()), 0.0)

        expected_return = theoretical_expected_return()
        self.assertAlmostEqual(expected_return["ticket_cost"], TICKET_COST_GBP)
        self.assertAlmostEqual(
            expected_return["expected_net_value"],
            expected_return["expected_prize_value"] - TICKET_COST_GBP,
        )

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
        self.assertIn("Estimated prize value", results.columns)
        self.assertIn("Estimated net value", results.columns)

        summary = summarise_backtest(results)
        self.assertIn("expected_prize_value", summary.columns)
        self.assertIn("roi", summary.columns)

        tier_values = summarise_prize_tier_values(results)
        self.assertIn("Total prize value", tier_values.columns)

    def test_behavioral_ticket_scoring_flags_human_like_patterns(self):
        human_like = analyse_ticket_behavior([7, 11, 21, 22, 30], [3, 7])
        anti_crowd = analyse_ticket_behavior([32, 37, 41, 46, 49], [1, 12])

        self.assertGreater(human_like.crowding_risk_score, anti_crowd.crowding_risk_score)
        self.assertGreater(human_like.birthday_bias_score, anti_crowd.birthday_bias_score)
        self.assertGreater(human_like.lucky_number_score, anti_crowd.lucky_number_score)
        self.assertAlmostEqual(human_like.anti_popularity_score, 1 - human_like.crowding_risk_score)

    def test_generate_anti_crowd_tickets_returns_valid_low_risk_tickets(self):
        tickets = generate_anti_crowd_tickets(count=3, simulations=100, random_seed=7)

        self.assertEqual(len(tickets), 3)
        self.assertEqual(
            [ticket.crowding_risk_score for ticket in tickets],
            sorted(ticket.crowding_risk_score for ticket in tickets),
        )
        for ticket in tickets:
            self.assertEqual(len(ticket.balls), 5)
            self.assertEqual(len(set(ticket.balls)), 5)
            self.assertTrue(all(1 <= number <= 50 for number in ticket.balls))
            self.assertEqual(len(ticket.stars), 2)
            self.assertEqual(len(set(ticket.stars)), 2)
            self.assertTrue(all(1 <= number <= 12 for number in ticket.stars))

if __name__ == "__main__":
    unittest.main()
