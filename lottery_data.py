from __future__ import annotations

import ast
import json
import math
import random
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


DATA_FILE = Path("euromillions_full_2004_2026.csv")
LEGACY_DATA_FILE = Path("euromillions_full_2004_2024.csv")
BALL_COUNT = 5
STAR_COUNT = 2
BALL_RANGE = range(1, 51)
STAR_RANGE = range(1, 13)
PRIZE_TIERS: dict[tuple[int, int], str] = {
    (5, 2): "5+2 Jackpot",
    (5, 1): "5+1",
    (5, 0): "5+0",
    (4, 2): "4+2",
    (4, 1): "4+1",
    (3, 2): "3+2",
    (4, 0): "4+0",
    (2, 2): "2+2",
    (3, 1): "3+1",
    (3, 0): "3+0",
    (1, 2): "1+2",
    (2, 1): "2+1",
    (2, 0): "2+0",
}
PRIZE_TIER_RANK: dict[str, int] = {tier: index for index, tier in enumerate(PRIZE_TIERS.values(), start=1)}
NO_PRIZE_TIER = "No prize"
TICKET_COST_GBP = 2.50
PRIZE_VALUE_SOURCE = (
    "Approximate UK EuroMillions tier values in GBP. Non-jackpot tiers use published expected "
    "prizes from the 2020 prize structure; jackpot uses a configurable illustrative value."
)
APPROXIMATE_PRIZE_VALUES_GBP: dict[str, float] = {
    "5+2 Jackpot": 52_000_000.0,
    "5+1": 169_001.0,
    "5+0": 17_555.0,
    "4+2": 1_094.0,
    "4+1": 101.0,
    "3+2": 48.0,
    "4+0": 33.0,
    "2+2": 12.0,
    "3+1": 9.0,
    "3+0": 8.0,
    "1+2": 6.0,
    "2+1": 5.0,
    "2+0": 3.0,
    NO_PRIZE_TIER: 0.0,
}
BACKTEST_RESULT_COLUMNS = [
    "Date",
    "Strategy",
    "Ball matches",
    "Star matches",
    "Total matches",
    "Prize tier",
    "Prize tier rank",
    "Prize hit",
    "Estimated prize value",
    "Estimated net value",
    "Ticket",
    "Actual",
    "Training draws",
    "Training through",
    "Config",
]
DEFAULT_SCORE_WEIGHTS: dict[str, float] = {
    "hot": 0.34,
    "cold": 0.16,
    "balance": 0.24,
    "spread": 0.11,
    "pair": 0.15,
}
MODEL_VARIANTS: dict[str, dict[str, float]] = {
    "Full model": DEFAULT_SCORE_WEIGHTS,
    "No hot score": {"hot": 0.0, "cold": 0.16, "balance": 0.24, "spread": 0.11, "pair": 0.15},
    "No cold score": {"hot": 0.34, "cold": 0.0, "balance": 0.24, "spread": 0.11, "pair": 0.15},
    "No balance score": {"hot": 0.34, "cold": 0.16, "balance": 0.0, "spread": 0.11, "pair": 0.15},
    "No spread score": {"hot": 0.34, "cold": 0.16, "balance": 0.24, "spread": 0.0, "pair": 0.15},
    "No pair score": {"hot": 0.34, "cold": 0.16, "balance": 0.24, "spread": 0.11, "pair": 0.0},
    "Only hot score": {"hot": 1.0, "cold": 0.0, "balance": 0.0, "spread": 0.0, "pair": 0.0},
    "Only pair score": {"hot": 0.0, "cold": 0.0, "balance": 0.0, "spread": 0.0, "pair": 1.0},
    "Only balance/spread": {"hot": 0.0, "cold": 0.0, "balance": 0.7, "spread": 0.3, "pair": 0.0},
}


@dataclass(frozen=True)
class TicketScore:
    balls: list[int]
    stars: list[int]
    score: float
    hot_score: float
    cold_score: float
    balance_score: float
    spread_score: float
    pair_score: float


@dataclass(frozen=True)
class BehavioralTicketScore:
    balls: list[int]
    stars: list[int]
    crowding_risk_score: float
    anti_popularity_score: float
    birthday_bias_score: float
    lucky_number_score: float
    round_number_score: float
    consecutive_score: float
    decade_cluster_score: float
    playslip_pattern_score: float
    star_popularity_score: float

def parse_number_list(value: object) -> list[int]:
    if isinstance(value, list):
        numbers = value
    elif pd.isna(value):
        raise ValueError("Missing number list")
    else:
        numbers = ast.literal_eval(str(value))

    if not isinstance(numbers, list):
        raise ValueError(f"Expected a list, got {type(numbers).__name__}")

    return [int(number) for number in numbers]


def _validate_numbers(numbers: list[int], *, expected_count: int, allowed_range: range, label: str) -> None:
    if len(numbers) != expected_count:
        raise ValueError(f"{label} must contain {expected_count} numbers: {numbers}")
    if len(set(numbers)) != expected_count:
        raise ValueError(f"{label} contains duplicates: {numbers}")
    outside_range = [number for number in numbers if number not in allowed_range]
    if outside_range:
        start = allowed_range.start
        stop = allowed_range.stop - 1
        raise ValueError(f"{label} contains values outside {start}-{stop}: {outside_range}")


def validate_draws(df: pd.DataFrame) -> None:
    required_columns = {"Balls", "LuckyStars"}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

    for index, row in df.iterrows():
        _validate_numbers(
            row["Balls"],
            expected_count=BALL_COUNT,
            allowed_range=BALL_RANGE,
            label=f"row {index} Balls",
        )
        _validate_numbers(
            row["LuckyStars"],
            expected_count=STAR_COUNT,
            allowed_range=STAR_RANGE,
            label=f"row {index} LuckyStars",
        )

    if "Date" in df.columns:
        dated_rows = df["Date"].notna()
        duplicate_dates = df.loc[dated_rows & df.duplicated("Date", keep=False), "Date"]
        if not duplicate_dates.empty:
            dates = sorted(duplicate_dates.dt.strftime("%Y-%m-%d").unique())
            raise ValueError(f"Duplicate draw dates: {dates}")


def normalize_draws(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Balls"] = df["Balls"].apply(parse_number_list)
    df["LuckyStars"] = df["LuckyStars"].apply(parse_number_list)

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    else:
        df.insert(0, "Date", pd.NaT)

    if "Year" not in df.columns:
        df.insert(1, "Year", df["Date"].dt.year.astype("Int64"))

    validate_draws(df)
    return df


def load_draws(path: str | Path = DATA_FILE) -> pd.DataFrame:
    path = Path(path)
    if path == DATA_FILE and not path.exists() and LEGACY_DATA_FILE.exists():
        path = LEGACY_DATA_FILE
    return normalize_draws(pd.read_csv(path))


def save_draws(df: pd.DataFrame, path: str | Path = DATA_FILE) -> None:
    output = df.copy()
    output["Date"] = output["Date"].dt.strftime("%Y-%m-%d")
    output["Date"] = output["Date"].fillna("")
    output["Balls"] = output["Balls"].apply(lambda numbers: str(sorted(numbers)))
    output["LuckyStars"] = output["LuckyStars"].apply(lambda numbers: str(sorted(numbers)))
    output.to_csv(path, index=False)


def append_new_draws(existing_path: str | Path, new_draws_path: str | Path) -> int:
    existing = load_draws(existing_path)
    new_draws = load_draws(new_draws_path)

    if new_draws["Date"].isna().any():
        raise ValueError("New draws must include a Date column with valid dates.")

    known_dates = set(existing["Date"].dropna())
    unseen_draws = new_draws[~new_draws["Date"].isin(known_dates)].copy()
    if unseen_draws.empty:
        return 0

    combined = pd.concat([existing, unseen_draws], ignore_index=True)
    combined = combined.sort_values(["Date", "Year"], na_position="first").reset_index(drop=True)
    validate_draws(combined)
    save_draws(combined, existing_path)
    return len(unseen_draws)


def get_top_numbers(df: pd.DataFrame, top_n: int = 10) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    balls = [number for draw in df["Balls"] for number in draw]
    stars = [number for draw in df["LuckyStars"] for number in draw]
    return Counter(balls).most_common(top_n), Counter(stars).most_common(max(2, min(5, top_n)))


def get_cold_numbers(df: pd.DataFrame, top_n: int = 10) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    balls = Counter(number for draw in df["Balls"] for number in draw)
    stars = Counter(number for draw in df["LuckyStars"] for number in draw)
    cold_balls = sorted(((number, balls[number]) for number in BALL_RANGE), key=lambda item: (item[1], item[0]))
    cold_stars = sorted(((number, stars[number]) for number in STAR_RANGE), key=lambda item: (item[1], item[0]))
    return cold_balls[:top_n], cold_stars[: max(2, min(5, top_n))]


def _normalise_scores(scores: dict[int, float], allowed_range: range) -> dict[int, float]:
    values = [scores.get(number, 0.0) for number in allowed_range]
    low = min(values)
    high = max(values)
    if high == low:
        return {number: 0.5 for number in allowed_range}
    return {number: (scores.get(number, 0.0) - low) / (high - low) for number in allowed_range}


def _normalise_score_weights(weights: dict[str, float] | None = None) -> dict[str, float]:
    merged = DEFAULT_SCORE_WEIGHTS.copy()
    if weights is not None:
        merged.update(weights)
    total = sum(max(0.0, value) for value in merged.values())
    if total <= 0:
        return DEFAULT_SCORE_WEIGHTS.copy()
    return {name: max(0.0, value) / total for name, value in merged.items()}


def _score_from_components(ticket: TicketScore, weights: dict[str, float] | None = None) -> float:
    normalised = _normalise_score_weights(weights)
    return (
        ticket.hot_score * normalised["hot"]
        + ticket.cold_score * normalised["cold"]
        + ticket.balance_score * normalised["balance"]
        + ticket.spread_score * normalised["spread"]
        + ticket.pair_score * normalised["pair"]
    )


def binomial_confidence_interval(successes: int, trials: int, confidence: float = 0.95) -> tuple[float, float]:
    if trials <= 0:
        return 0.0, 0.0

    z_scores = {0.8: 1.2815515655446004, 0.9: 1.6448536269514722, 0.95: 1.959963984540054}
    z = z_scores.get(confidence, 1.959963984540054)
    proportion = successes / trials
    denominator = 1 + z**2 / trials
    centre = proportion + z**2 / (2 * trials)
    margin = z * math.sqrt((proportion * (1 - proportion) + z**2 / (4 * trials)) / trials)
    return max(0.0, (centre - margin) / denominator), min(1.0, (centre + margin) / denominator)


def mean_confidence_interval(values: pd.Series, confidence: float = 0.95) -> tuple[float, float]:
    clean = values.dropna()
    if clean.empty:
        return 0.0, 0.0
    if len(clean) == 1:
        value = float(clean.iloc[0])
        return value, value

    z_scores = {0.8: 1.2815515655446004, 0.9: 1.6448536269514722, 0.95: 1.959963984540054}
    z = z_scores.get(confidence, 1.959963984540054)
    mean = float(clean.mean())
    margin = z * float(clean.std(ddof=1)) / math.sqrt(len(clean))
    return mean - margin, mean + margin


def prize_tier(ball_matches: int, star_matches: int) -> str:
    return PRIZE_TIERS.get((ball_matches, star_matches), NO_PRIZE_TIER)


def prize_tier_rank(tier: str) -> int:
    return PRIZE_TIER_RANK.get(tier, len(PRIZE_TIER_RANK) + 1)


def estimated_prize_value(tier: str, prize_values: dict[str, float] | None = None) -> float:
    values = APPROXIMATE_PRIZE_VALUES_GBP if prize_values is None else {**APPROXIMATE_PRIZE_VALUES_GBP, **prize_values}
    return float(values.get(tier, 0.0))


def prize_value_table(prize_values: dict[str, float] | None = None) -> pd.DataFrame:
    values = APPROXIMATE_PRIZE_VALUES_GBP if prize_values is None else {**APPROXIMATE_PRIZE_VALUES_GBP, **prize_values}
    rows = [
        {
            "Prize tier": tier,
            "Estimated prize value": estimated_prize_value(tier, values),
            "Tier rank": prize_tier_rank(tier),
            "Source note": PRIZE_VALUE_SOURCE,
        }
        for tier in list(PRIZE_TIERS.values()) + [NO_PRIZE_TIER]
    ]
    return pd.DataFrame(rows).sort_values("Tier rank").reset_index(drop=True)


def ensure_backtest_schema(results: pd.DataFrame) -> pd.DataFrame:
    normalised = results.copy()

    if normalised.empty:
        for column in BACKTEST_RESULT_COLUMNS:
            if column not in normalised.columns:
                normalised[column] = pd.Series(dtype="object")
        return normalised[BACKTEST_RESULT_COLUMNS]

    if "Total matches" not in normalised.columns and {"Ball matches", "Star matches"}.issubset(normalised.columns):
        normalised["Total matches"] = normalised["Ball matches"] + normalised["Star matches"]

    if "Prize tier" not in normalised.columns and {"Ball matches", "Star matches"}.issubset(normalised.columns):
        normalised["Prize tier"] = [
            prize_tier(int(ball_matches), int(star_matches))
            for ball_matches, star_matches in zip(normalised["Ball matches"], normalised["Star matches"])
        ]

    if "Prize tier rank" not in normalised.columns and "Prize tier" in normalised.columns:
        normalised["Prize tier rank"] = normalised["Prize tier"].apply(prize_tier_rank)

    if "Prize hit" not in normalised.columns and "Prize tier" in normalised.columns:
        normalised["Prize hit"] = normalised["Prize tier"] != NO_PRIZE_TIER

    if "Estimated prize value" not in normalised.columns and "Prize tier" in normalised.columns:
        normalised["Estimated prize value"] = normalised["Prize tier"].apply(estimated_prize_value)

    if "Estimated net value" not in normalised.columns and "Estimated prize value" in normalised.columns:
        normalised["Estimated net value"] = normalised["Estimated prize value"] - TICKET_COST_GBP

    for column in BACKTEST_RESULT_COLUMNS:
        if column not in normalised.columns:
            normalised[column] = pd.NA

    return normalised


def _comb(total: int, selected: int) -> int:
    if selected < 0 or selected > total:
        return 0
    selected = min(selected, total - selected)
    result = 1
    for number in range(1, selected + 1):
        result = result * (total - selected + number) // number
    return result


def theoretical_expected_matches() -> dict[str, float]:
    return {
        "ball_matches": BALL_COUNT * BALL_COUNT / len(BALL_RANGE),
        "star_matches": STAR_COUNT * STAR_COUNT / len(STAR_RANGE),
        "total_matches": BALL_COUNT * BALL_COUNT / len(BALL_RANGE) + STAR_COUNT * STAR_COUNT / len(STAR_RANGE),
    }


def theoretical_prize_probabilities(
    *,
    ticket_cost: float = TICKET_COST_GBP,
    prize_values: dict[str, float] | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    total_ball_combinations = _comb(len(BALL_RANGE), BALL_COUNT)
    total_star_combinations = _comb(len(STAR_RANGE), STAR_COUNT)

    for ball_matches in range(BALL_COUNT + 1):
        ball_probability = (
            _comb(BALL_COUNT, ball_matches)
            * _comb(len(BALL_RANGE) - BALL_COUNT, BALL_COUNT - ball_matches)
            / total_ball_combinations
        )
        for star_matches in range(STAR_COUNT + 1):
            star_probability = (
                _comb(STAR_COUNT, star_matches)
                * _comb(len(STAR_RANGE) - STAR_COUNT, STAR_COUNT - star_matches)
                / total_star_combinations
            )
            tier = prize_tier(ball_matches, star_matches)
            if tier == NO_PRIZE_TIER:
                continue
            probability = ball_probability * star_probability
            prize_value = estimated_prize_value(tier, prize_values)
            rows.append(
                {
                    "Prize tier": tier,
                    "Ball matches": ball_matches,
                    "Star matches": star_matches,
                    "Probability": probability,
                    "Odds 1 in": 1 / probability,
                    "Tier rank": prize_tier_rank(tier),
                    "Estimated prize value": prize_value,
                    "Expected value contribution": probability * prize_value,
                }
            )

    frame = pd.DataFrame(rows).sort_values("Tier rank").reset_index(drop=True)
    frame["Ticket cost"] = ticket_cost
    frame["Source note"] = PRIZE_VALUE_SOURCE
    return frame


def theoretical_expected_return(
    *,
    ticket_cost: float = TICKET_COST_GBP,
    prize_values: dict[str, float] | None = None,
) -> dict[str, float]:
    odds = theoretical_prize_probabilities(ticket_cost=ticket_cost, prize_values=prize_values)
    gross = float(odds["Expected value contribution"].sum()) if not odds.empty else 0.0
    return {
        "expected_prize_value": gross,
        "ticket_cost": ticket_cost,
        "expected_net_value": gross - ticket_cost,
        "expected_return_ratio": gross / ticket_cost if ticket_cost else 0.0,
        "expected_roi": (gross - ticket_cost) / ticket_cost if ticket_cost else 0.0,
    }


def get_weighted_number_scores(
    df: pd.DataFrame,
    *,
    half_life: int = 75,
) -> tuple[dict[int, float], dict[int, float]]:
    """Return recency-weighted ball and star scores between 0 and 1."""
    ordered = df.dropna(subset=["Date"]).sort_values("Date")
    if ordered.empty:
        ordered = df.reset_index(drop=True)

    ball_scores = {number: 0.0 for number in BALL_RANGE}
    star_scores = {number: 0.0 for number in STAR_RANGE}
    total_draws = len(ordered)
    decay_base = 0.5 ** (1 / max(1, half_life))

    for position, row in enumerate(ordered.itertuples(index=False)):
        age = total_draws - position - 1
        weight = decay_base**age
        for number in row.Balls:
            ball_scores[number] += weight
        for number in row.LuckyStars:
            star_scores[number] += weight

    return _normalise_scores(ball_scores, BALL_RANGE), _normalise_scores(star_scores, STAR_RANGE)


def get_pair_scores(df: pd.DataFrame, *, half_life: int = 75) -> dict[tuple[int, int], float]:
    ordered = df.dropna(subset=["Date"]).sort_values("Date")
    if ordered.empty:
        ordered = df.reset_index(drop=True)

    pair_scores: dict[tuple[int, int], float] = {}
    total_draws = len(ordered)
    decay_base = 0.5 ** (1 / max(1, half_life))

    for position, row in enumerate(ordered.itertuples(index=False)):
        age = total_draws - position - 1
        weight = decay_base**age
        balls = sorted(row.Balls)
        for first_index, first in enumerate(balls):
            for second in balls[first_index + 1 :]:
                pair_scores[(first, second)] = pair_scores.get((first, second), 0.0) + weight

    if not pair_scores:
        return {}

    high = max(pair_scores.values())
    return {pair: score / high for pair, score in pair_scores.items()}

def score_ticket(
    balls: list[int],
    stars: list[int],
    df: pd.DataFrame,
    *,
    half_life: int = 75,
    score_weights: dict[str, float] | None = None,
) -> TicketScore:
    ball_scores, star_scores = get_weighted_number_scores(df, half_life=half_life)
    pair_scores = get_pair_scores(df, half_life=half_life)
    return _score_ticket_with_model(balls, stars, ball_scores, star_scores, pair_scores, score_weights=score_weights)


def _score_ticket_with_model(
    balls: list[int],
    stars: list[int],
    ball_scores: dict[int, float],
    star_scores: dict[int, float],
    pair_scores: dict[tuple[int, int], float],
    *,
    score_weights: dict[str, float] | None = None,
) -> TicketScore:

    hot_score = (
        sum(ball_scores[number] for number in balls) / BALL_COUNT * 0.75
        + sum(star_scores[number] for number in stars) / STAR_COUNT * 0.25
    )

    cold_score = (
        sum(1 - ball_scores[number] for number in balls) / BALL_COUNT * 0.75
        + sum(1 - star_scores[number] for number in stars) / STAR_COUNT * 0.25
    )

    odd_count = sum(number % 2 for number in balls)
    low_count = sum(number <= 25 for number in balls)
    odd_even_score = 1 - abs(odd_count - 2.5) / 2.5
    low_high_score = 1 - abs(low_count - 2.5) / 2.5
    total = sum(balls)
    sum_score = max(0.0, 1 - abs(total - 127.5) / 90)
    balance_score = (odd_even_score + low_high_score + sum_score) / 3

    spread = max(balls) - min(balls)
    spread_score = max(0.0, 1 - abs(spread - 36) / 36)

    pairs = [
        tuple(sorted((first, second)))
        for first_index, first in enumerate(balls)
        for second in balls[first_index + 1 :]
    ]
    pair_score = sum(pair_scores.get(pair, 0.0) for pair in pairs) / len(pairs)

    normalised_weights = _normalise_score_weights(score_weights)
    score = (
        hot_score * normalised_weights["hot"]
        + cold_score * normalised_weights["cold"]
        + balance_score * normalised_weights["balance"]
        + spread_score * normalised_weights["spread"]
        + pair_score * normalised_weights["pair"]
    )

    return TicketScore(
        balls=sorted(balls),
        stars=sorted(stars),
        score=score,
        hot_score=hot_score,
        cold_score=cold_score,
        balance_score=balance_score,
        spread_score=spread_score,
        pair_score=pair_score,
    )


def filter_recent_draws(df: pd.DataFrame, draw_count: int) -> pd.DataFrame:
    dated = df.dropna(subset=["Date"]).sort_values("Date")
    if dated.empty:
        return df.tail(draw_count)
    return dated.tail(draw_count)


def generate_ticket(
    candidates: tuple[list[tuple[int, int]], list[tuple[int, int]]],
    rng: random.Random | None = None,
) -> tuple[list[int], list[int]]:
    top_balls, top_stars = candidates
    if len(top_balls) < BALL_COUNT or len(top_stars) < STAR_COUNT:
        raise ValueError("Not enough candidate numbers to generate a ticket.")

    generator = rng or random
    balls = sorted(generator.sample([number for number, _ in top_balls], BALL_COUNT))
    stars = sorted(generator.sample([number for number, _ in top_stars], STAR_COUNT))
    return balls, stars


def generate_random_ticket(rng: random.Random | None = None) -> tuple[list[int], list[int]]:
    generator = rng or random
    balls = sorted(generator.sample(list(BALL_RANGE), BALL_COUNT))
    stars = sorted(generator.sample(list(STAR_RANGE), STAR_COUNT))
    return balls, stars


def analyse_ticket_behavior(balls: list[int], stars: list[int]) -> BehavioralTicketScore:
    _validate_numbers(balls, expected_count=BALL_COUNT, allowed_range=BALL_RANGE, label="Balls")
    _validate_numbers(stars, expected_count=STAR_COUNT, allowed_range=STAR_RANGE, label="LuckyStars")

    sorted_balls = sorted(balls)
    sorted_stars = sorted(stars)
    lucky_numbers = {3, 7, 8, 11, 13, 21, 22, 33}
    popular_stars = {3, 7, 11}

    birthday_bias_score = sum(number <= 31 for number in sorted_balls) / BALL_COUNT
    lucky_number_score = (
        sum(number in lucky_numbers for number in sorted_balls) / BALL_COUNT * 0.75
        + sum(number in popular_stars for number in sorted_stars) / STAR_COUNT * 0.25
    )
    round_number_score = sum(number % 10 == 0 or number == 50 for number in sorted_balls) / BALL_COUNT
    consecutive_pairs = sum(
        1 for first, second in zip(sorted_balls, sorted_balls[1:]) if second - first == 1
    )
    consecutive_score = consecutive_pairs / (BALL_COUNT - 1)

    decade_counts = Counter((number - 1) // 10 for number in sorted_balls)
    decade_cluster_score = (max(decade_counts.values()) - 1) / (BALL_COUNT - 1)

    terminal_digit_counts = Counter(number % 10 for number in sorted_balls)
    same_column_score = (max(terminal_digit_counts.values()) - 1) / (BALL_COUNT - 1)
    visual_pattern_score = (consecutive_score + decade_cluster_score + same_column_score) / 3

    star_popularity_score = sum(number in popular_stars for number in sorted_stars) / STAR_COUNT
    crowding_risk_score = (
        birthday_bias_score * 0.38
        + lucky_number_score * 0.18
        + round_number_score * 0.12
        + visual_pattern_score * 0.22
        + star_popularity_score * 0.10
    )
    crowding_risk_score = max(0.0, min(1.0, crowding_risk_score))

    return BehavioralTicketScore(
        balls=sorted_balls,
        stars=sorted_stars,
        crowding_risk_score=crowding_risk_score,
        anti_popularity_score=1 - crowding_risk_score,
        birthday_bias_score=birthday_bias_score,
        lucky_number_score=lucky_number_score,
        round_number_score=round_number_score,
        consecutive_score=consecutive_score,
        decade_cluster_score=decade_cluster_score,
        playslip_pattern_score=visual_pattern_score,
        star_popularity_score=star_popularity_score,
    )


def generate_anti_crowd_tickets(
    *,
    count: int = 5,
    simulations: int = 2000,
    random_seed: int = 42,
) -> list[BehavioralTicketScore]:
    if count <= 0:
        return []

    rng = random.Random(random_seed)
    seen: set[tuple[tuple[int, ...], tuple[int, ...]]] = set()
    scored_tickets: list[BehavioralTicketScore] = []

    while len(scored_tickets) < simulations:
        balls, stars = generate_random_ticket(rng)
        key = (tuple(balls), tuple(stars))
        if key in seen:
            continue
        seen.add(key)
        scored_tickets.append(analyse_ticket_behavior(balls, stars))

    return sorted(
        scored_tickets,
        key=lambda ticket: (
            ticket.crowding_risk_score,
            ticket.birthday_bias_score,
            ticket.playslip_pattern_score,
            ticket.balls,
            ticket.stars,
        ),
    )[:count]


def generate_ranked_tickets(
    df: pd.DataFrame,
    *,
    simulations: int = 1000,
    half_life: int = 75,
    top_k: int = 5,
    random_seed: int = 42,
    score_weights: dict[str, float] | None = None,
) -> list[TicketScore]:
    rng = random.Random(random_seed)
    seen: set[tuple[tuple[int, ...], tuple[int, ...]]] = set()
    scored_tickets: list[TicketScore] = []
    ball_scores, star_scores = get_weighted_number_scores(df, half_life=half_life)
    pair_scores = get_pair_scores(df, half_life=half_life)

    while len(scored_tickets) < simulations:
        balls, stars = generate_random_ticket(rng)
        key = (tuple(balls), tuple(stars))
        if key in seen:
            continue
        seen.add(key)
        scored_tickets.append(
            _score_ticket_with_model(
                balls,
                stars,
                ball_scores,
                star_scores,
                pair_scores,
                score_weights=score_weights,
            )
        )

    return sorted(scored_tickets, key=lambda ticket: ticket.score, reverse=True)[:top_k]


def generate_balanced_ticket(
    df: pd.DataFrame,
    recent_draw_count: int = 100,
    rng: random.Random | None = None,
) -> tuple[list[int], list[int]]:
    recent = filter_recent_draws(df, recent_draw_count)
    hot_balls, hot_stars = get_top_numbers(recent, top_n=20)
    cold_balls, cold_stars = get_cold_numbers(df, top_n=20)

    ball_pool = list(dict.fromkeys([number for number, _ in hot_balls[:12] + cold_balls[:8]]))
    star_pool = list(dict.fromkeys([number for number, _ in hot_stars[:4] + cold_stars[:4]]))

    generator = rng or random
    balls = sorted(generator.sample(ball_pool, BALL_COUNT))
    stars = sorted(generator.sample(star_pool, STAR_COUNT))
    return balls, stars


def score_match(ticket: tuple[list[int], list[int]], draw: tuple[list[int], list[int]]) -> tuple[int, int]:
    ticket_balls, ticket_stars = ticket
    draw_balls, draw_stars = draw
    return len(set(ticket_balls) & set(draw_balls)), len(set(ticket_stars) & set(draw_stars))


def backtest_strategies(
    df: pd.DataFrame,
    *,
    training_window: int = 300,
    history_window: int | None = None,
    test_draws: int = 250,
    recent_draw_count: int = 100,
    simulations: int = 300,
    half_life: int = 75,
    random_seed: int = 42,
) -> pd.DataFrame:
    ordered = df.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)
    if ordered.empty:
        ordered = df.reset_index(drop=True)

    start = max(training_window, len(ordered) - test_draws)
    rng = random.Random(random_seed)
    rows: list[dict[str, object]] = []
    config = {
        "training_window": training_window,
        "history_window": history_window,
        "test_draws": test_draws,
        "recent_draw_count": recent_draw_count,
        "simulations": simulations,
        "half_life": half_life,
        "random_seed": random_seed,
    }

    for index in range(start, len(ordered)):
        history_start = max(0, index - history_window) if history_window is not None else 0
        history = ordered.iloc[history_start:index].copy()
        actual = (ordered.iloc[index]["Balls"], ordered.iloc[index]["LuckyStars"])

        ranked_ticket = generate_ranked_tickets(
            history,
            simulations=simulations,
            half_life=half_life,
            top_k=1,
            random_seed=random_seed + index,
        )[0]

        strategies = {
            "Random baseline": generate_random_ticket(rng),
            "Recent hot": generate_ticket(get_top_numbers(filter_recent_draws(history, recent_draw_count), 20), rng),
            "Cold numbers": generate_ticket(get_cold_numbers(history, 20), rng),
            "Balanced mix": generate_balanced_ticket(history, recent_draw_count, rng),
            "Ranked model": (ranked_ticket.balls, ranked_ticket.stars),
        }

        for strategy, ticket in strategies.items():
            ball_matches, star_matches = score_match(ticket, actual)
            tier = prize_tier(ball_matches, star_matches)
            rows.append(
                {
                    "Date": ordered.iloc[index]["Date"],
                    "Strategy": strategy,
                    "Ball matches": ball_matches,
                    "Star matches": star_matches,
                    "Total matches": ball_matches + star_matches,
                    "Prize tier": tier,
                    "Prize tier rank": prize_tier_rank(tier),
                    "Prize hit": tier != NO_PRIZE_TIER,
                    "Estimated prize value": estimated_prize_value(tier),
                    "Estimated net value": estimated_prize_value(tier) - TICKET_COST_GBP,
                    "Ticket": f"{ticket[0]} | {ticket[1]}",
                    "Actual": f"{actual[0]} | {actual[1]}",
                    "Training draws": len(history),
                    "Training through": history["Date"].max() if "Date" in history.columns else pd.NaT,
                    "Config": json.dumps(config, sort_keys=True),
                }
            )

    return ensure_backtest_schema(pd.DataFrame(rows))


def summarise_backtest(results: pd.DataFrame, *, confidence: float = 0.95) -> pd.DataFrame:
    results = ensure_backtest_schema(results)
    rows: list[dict[str, object]] = []

    if results.empty:
        return pd.DataFrame(
            columns=[
                "Strategy",
                "draws",
                "avg_ball_matches",
                "avg_star_matches",
                "avg_total_matches",
                "total_ci_low",
                "total_ci_high",
                "prize_hits",
                "prize_hit_rate",
                "hit_ci_low",
                "hit_ci_high",
                "expected_prize_value",
                "expected_net_value",
                "return_ratio",
                "roi",
                "total_prize_value",
                "best_prize_tier",
                "best_prize_rank",
                "best_prize_value",
            ]
        )

    for strategy, group in results.groupby("Strategy"):
        hit_count = int(group["Prize hit"].sum())
        draws = int(group["Date"].count())
        hit_low, hit_high = binomial_confidence_interval(hit_count, draws, confidence)
        total_low, total_high = mean_confidence_interval(group["Total matches"], confidence)
        prize_ranks = group.loc[group["Prize hit"], "Prize tier rank"]
        best_rank = int(prize_ranks.min()) if not prize_ranks.empty else prize_tier_rank(NO_PRIZE_TIER)
        best_tier = next((tier for tier, rank in PRIZE_TIER_RANK.items() if rank == best_rank), NO_PRIZE_TIER)
        expected_prize_value = float(group["Estimated prize value"].mean()) if draws else 0.0
        expected_net_value = expected_prize_value - TICKET_COST_GBP

        rows.append(
            {
                "Strategy": strategy,
                "draws": draws,
                "avg_ball_matches": float(group["Ball matches"].mean()),
                "avg_star_matches": float(group["Star matches"].mean()),
                "avg_total_matches": float(group["Total matches"].mean()),
                "total_ci_low": total_low,
                "total_ci_high": total_high,
                "prize_hits": hit_count,
                "prize_hit_rate": hit_count / draws if draws else 0.0,
                "hit_ci_low": hit_low,
                "hit_ci_high": hit_high,
                "expected_prize_value": expected_prize_value,
                "expected_net_value": expected_net_value,
                "return_ratio": expected_prize_value / TICKET_COST_GBP if TICKET_COST_GBP else 0.0,
                "roi": expected_net_value / TICKET_COST_GBP if TICKET_COST_GBP else 0.0,
                "total_prize_value": float(group["Estimated prize value"].sum()),
                "best_prize_tier": best_tier,
                "best_prize_rank": best_rank,
                "best_prize_value": estimated_prize_value(best_tier),
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values(["expected_prize_value", "prize_hit_rate", "avg_total_matches"], ascending=False)
        .reset_index(drop=True)
    )


def summarise_prize_tier_values(results: pd.DataFrame) -> pd.DataFrame:
    results = ensure_backtest_schema(results)
    if results.empty:
        return pd.DataFrame(
            columns=[
                "Strategy",
                "Prize tier",
                "Hits",
                "Hit rate",
                "Estimated prize value",
                "Total prize value",
                "Share of strategy value",
            ]
        )

    grouped = (
        results[results["Prize hit"]]
        .groupby(["Strategy", "Prize tier", "Prize tier rank"], as_index=False)
        .agg(Hits=("Prize tier", "size"), **{"Total prize value": ("Estimated prize value", "sum")})
    )
    draws = results.groupby("Strategy").size().rename("draws")
    totals = grouped.groupby("Strategy")["Total prize value"].sum().rename("strategy_value")
    grouped = grouped.join(draws, on="Strategy").join(totals, on="Strategy")
    grouped["Hit rate"] = grouped["Hits"] / grouped["draws"]
    grouped["Estimated prize value"] = grouped["Prize tier"].apply(estimated_prize_value)
    grouped["Share of strategy value"] = grouped["Total prize value"] / grouped["strategy_value"]
    grouped["Share of strategy value"] = grouped["Share of strategy value"].fillna(0.0)
    return (
        grouped[
            [
                "Strategy",
                "Prize tier",
                "Hits",
                "Hit rate",
                "Estimated prize value",
                "Total prize value",
                "Share of strategy value",
                "Prize tier rank",
            ]
        ]
        .sort_values(["Strategy", "Total prize value", "Prize tier rank"], ascending=[True, False, True])
        .reset_index(drop=True)
    )


def summarise_match_distribution(results: pd.DataFrame) -> pd.DataFrame:
    results = ensure_backtest_schema(results)
    rows: list[dict[str, object]] = []

    if results.empty:
        return pd.DataFrame(
            columns=[
                "Strategy",
                "draws",
                "match_0_rate",
                "match_1_rate",
                "match_2_rate",
                "match_3_plus_rate",
                "max_total_matches",
                "total_match_std",
            ]
        )

    for strategy, group in results.groupby("Strategy"):
        draws = len(group)
        counts = group["Total matches"].value_counts().to_dict()
        rows.append(
            {
                "Strategy": strategy,
                "draws": draws,
                "match_0_rate": counts.get(0, 0) / draws if draws else 0.0,
                "match_1_rate": counts.get(1, 0) / draws if draws else 0.0,
                "match_2_rate": counts.get(2, 0) / draws if draws else 0.0,
                "match_3_plus_rate": int((group["Total matches"] >= 3).sum()) / draws if draws else 0.0,
                "max_total_matches": int(group["Total matches"].max()) if draws else 0,
                "total_match_std": float(group["Total matches"].std(ddof=0)) if draws else 0.0,
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values(["match_3_plus_rate", "match_2_rate", "match_1_rate"], ascending=False)
        .reset_index(drop=True)
    )


def run_repeated_backtests(
    df: pd.DataFrame,
    *,
    seeds: list[int],
    training_window: int = 300,
    test_draws: int = 100,
    recent_draw_count: int = 100,
    simulations: int = 300,
    half_life: int = 75,
) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []

    for seed in seeds:
        results = backtest_strategies(
            df,
            training_window=training_window,
            test_draws=test_draws,
            recent_draw_count=recent_draw_count,
            simulations=simulations,
            half_life=half_life,
            random_seed=seed,
        )
        summary = summarise_backtest(results)
        summary.insert(0, "seed", seed)
        rows.append(summary)

    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True)


def backtest_model_ablation(
    df: pd.DataFrame,
    *,
    variants: dict[str, dict[str, float]] | None = None,
    training_window: int = 300,
    history_window: int | None = None,
    test_draws: int = 100,
    simulations: int = 100,
    half_life: int = 75,
    random_seed: int = 42,
) -> pd.DataFrame:
    ordered = df.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)
    if ordered.empty:
        ordered = df.reset_index(drop=True)

    model_variants = variants or MODEL_VARIANTS
    start = max(training_window, len(ordered) - test_draws)
    rows: list[dict[str, object]] = []

    for index in range(start, len(ordered)):
        history_start = max(0, index - history_window) if history_window is not None else 0
        history = ordered.iloc[history_start:index].copy()
        actual = (ordered.iloc[index]["Balls"], ordered.iloc[index]["LuckyStars"])

        for variant_name, score_weights in model_variants.items():
            ranked_ticket = generate_ranked_tickets(
                history,
                simulations=simulations,
                half_life=half_life,
                top_k=1,
                random_seed=random_seed + index,
                score_weights=score_weights,
            )[0]
            ticket = (ranked_ticket.balls, ranked_ticket.stars)
            ball_matches, star_matches = score_match(ticket, actual)
            tier = prize_tier(ball_matches, star_matches)
            rows.append(
                {
                    "Date": ordered.iloc[index]["Date"],
                    "Strategy": variant_name,
                    "Ball matches": ball_matches,
                    "Star matches": star_matches,
                    "Total matches": ball_matches + star_matches,
                    "Prize tier": tier,
                    "Prize tier rank": prize_tier_rank(tier),
                    "Prize hit": tier != NO_PRIZE_TIER,
                    "Estimated prize value": estimated_prize_value(tier),
                    "Estimated net value": estimated_prize_value(tier) - TICKET_COST_GBP,
                    "Ticket": f"{ticket[0]} | {ticket[1]}",
                    "Actual": f"{actual[0]} | {actual[1]}",
                    "Training draws": len(history),
                    "Training through": history["Date"].max() if "Date" in history.columns else pd.NaT,
                    "Config": json.dumps(
                        {
                            "training_window": training_window,
                            "history_window": history_window,
                            "test_draws": test_draws,
                            "simulations": simulations,
                            "half_life": half_life,
                            "random_seed": random_seed,
                            "variant": variant_name,
                            "score_weights": _normalise_score_weights(score_weights),
                        },
                        sort_keys=True,
                    ),
                }
            )

    return ensure_backtest_schema(pd.DataFrame(rows))


def summarise_repeated_backtests(repeated: pd.DataFrame, *, confidence: float = 0.95) -> pd.DataFrame:
    if repeated.empty:
        return repeated

    rows: list[dict[str, object]] = []
    random_rows = repeated[repeated["Strategy"] == "Random baseline"].set_index("seed")

    for strategy, group in repeated.groupby("Strategy"):
        total_low, total_high = mean_confidence_interval(group["avg_total_matches"], confidence)
        hit_low, hit_high = mean_confidence_interval(group["prize_hit_rate"], confidence)
        value_low, value_high = mean_confidence_interval(group["expected_prize_value"], confidence)
        paired = group.set_index("seed")
        common_seeds = paired.index.intersection(random_rows.index)
        if strategy == "Random baseline" or common_seeds.empty:
            win_rate_vs_random = None
            avg_edge_vs_random = None
            avg_value_edge_vs_random = None
        else:
            total_edges = paired.loc[common_seeds, "avg_total_matches"] - random_rows.loc[common_seeds, "avg_total_matches"]
            hit_edges = paired.loc[common_seeds, "prize_hit_rate"] - random_rows.loc[common_seeds, "prize_hit_rate"]
            value_edges = (
                paired.loc[common_seeds, "expected_prize_value"]
                - random_rows.loc[common_seeds, "expected_prize_value"]
            )
            win_rate_vs_random = float((total_edges > 0).mean())
            avg_edge_vs_random = float(total_edges.mean())
            avg_hit_edge_vs_random = float(hit_edges.mean())
            avg_value_edge_vs_random = float(value_edges.mean())

        if strategy == "Random baseline" or common_seeds.empty:
            avg_hit_edge_vs_random = None

        rows.append(
            {
                "Strategy": strategy,
                "runs": int(group["seed"].nunique()),
                "mean_total_matches": float(group["avg_total_matches"].mean()),
                "total_ci_low": total_low,
                "total_ci_high": total_high,
                "mean_prize_hit_rate": float(group["prize_hit_rate"].mean()),
                "hit_ci_low": hit_low,
                "hit_ci_high": hit_high,
                "mean_expected_prize_value": float(group["expected_prize_value"].mean()),
                "value_ci_low": value_low,
                "value_ci_high": value_high,
                "mean_expected_net_value": float(group["expected_net_value"].mean()),
                "mean_roi": float(group["roi"].mean()),
                "win_rate_vs_random": win_rate_vs_random,
                "avg_total_edge_vs_random": avg_edge_vs_random,
                "avg_hit_edge_vs_random": avg_hit_edge_vs_random,
                "avg_value_edge_vs_random": avg_value_edge_vs_random,
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values(["mean_expected_prize_value", "mean_prize_hit_rate", "mean_total_matches"], ascending=False)
        .reset_index(drop=True)
    )


def run_parameter_sweep(
    df: pd.DataFrame,
    *,
    half_lives: list[int],
    simulation_counts: list[int],
    training_window: int = 300,
    training_windows: list[int] | None = None,
    test_draws: int = 100,
    recent_draw_count: int = 100,
    recent_draw_counts: list[int] | None = None,
    random_seed: int = 42,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    training_options = training_windows or [training_window]
    recent_options = recent_draw_counts or [recent_draw_count]

    for active_training_window in training_options:
        for active_recent_draw_count in recent_options:
            for half_life in half_lives:
                for simulations in simulation_counts:
                    results = backtest_strategies(
                        df,
                        training_window=active_training_window,
                        history_window=active_training_window,
                        test_draws=test_draws,
                        recent_draw_count=active_recent_draw_count,
                        simulations=simulations,
                        half_life=half_life,
                        random_seed=random_seed,
                    )
                    summary = summarise_backtest(results)
                    distribution = summarise_match_distribution(results)
                    ranked = summary[summary["Strategy"] == "Ranked model"].iloc[0]
                    ranked_distribution = distribution[distribution["Strategy"] == "Ranked model"].iloc[0]
                    rows.append(
                        {
                            "half_life": half_life,
                            "simulations": simulations,
                            "training_window": active_training_window,
                            "test_draws": test_draws,
                            "recent_draw_count": active_recent_draw_count,
                            "avg_total_matches": ranked["avg_total_matches"],
                            "total_ci_low": ranked["total_ci_low"],
                            "total_ci_high": ranked["total_ci_high"],
                            "prize_hit_rate": ranked["prize_hit_rate"],
                            "hit_ci_low": ranked["hit_ci_low"],
                            "hit_ci_high": ranked["hit_ci_high"],
                            "expected_prize_value": ranked["expected_prize_value"],
                            "expected_net_value": ranked["expected_net_value"],
                            "return_ratio": ranked["return_ratio"],
                            "roi": ranked["roi"],
                            "match_0_rate": ranked_distribution["match_0_rate"],
                            "match_1_rate": ranked_distribution["match_1_rate"],
                            "match_2_rate": ranked_distribution["match_2_rate"],
                            "match_3_plus_rate": ranked_distribution["match_3_plus_rate"],
                            "total_match_std": ranked_distribution["total_match_std"],
                            "best_prize_tier": ranked["best_prize_tier"],
                        }
                    )

    return pd.DataFrame(rows).sort_values(["expected_prize_value", "prize_hit_rate", "avg_total_matches"], ascending=False)


def save_backtest_run(
    results: pd.DataFrame,
    output_dir: str | Path = "backtest_runs",
    *,
    config: dict[str, object] | None = None,
    name: str = "backtest",
) -> tuple[Path, Path]:
    results = ensure_backtest_schema(results)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    timestamp = pd.Timestamp.utcnow().strftime("%Y%m%d_%H%M%S")
    stem = f"{timestamp}_{name}"
    csv_path = output_path / f"{stem}.csv"
    json_path = output_path / f"{stem}.json"

    results.to_csv(csv_path, index=False)
    payload = {
        "config": config or {},
        "created_at": pd.Timestamp.utcnow().isoformat(),
        "rows": results.to_dict(orient="records"),
    }
    json_path.write_text(json.dumps(payload, default=str, indent=2), encoding="utf-8")
    return csv_path, json_path


def data_freshness_label(df: pd.DataFrame) -> str:
    dated = df["Date"].dropna()
    if dated.empty:
        years = sorted(df["Year"].dropna().astype(int).unique())
        if not years:
            return "Date unavailable"
        return f"Historical dataset through {years[-1]} (draw dates not stored)"
    return f"Dataset updated through {dated.max().date().isoformat()}"
