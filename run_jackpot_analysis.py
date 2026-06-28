#!/usr/bin/env python

from __future__ import annotations

import argparse
import math
import re
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd

from lottery_data import load_draws


RESULT_URL = "https://www.lottery.co.uk/euromillions/results-{date_slug}"
OUTPUT_DIR = Path("analysis_outputs")
HTML_CACHE_DIR = OUTPUT_DIR / "jackpot_pages"
DETAILS_FILE = OUTPUT_DIR / "jackpot_draw_details.csv"
SUMMARY_FILE = OUTPUT_DIR / "jackpot_win_patterns_summary.csv"


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if text:
            self.parts.append(text)


@dataclass(frozen=True)
class JackpotPageDetails:
    jackpot_prize_gbp: float | None
    uk_jackpot_winners: int | None
    total_jackpot_winners: int | None
    rollover_count: int | None
    winning_ticket_info: str
    ball_set: int | None
    ball_machine: int | None


def _money_to_float(value: str) -> float:
    cleaned = value.replace("£", "").replace(",", "").strip()
    return float(cleaned)


def _int_from_text(value: str) -> int:
    return int(value.replace(",", "").strip())


def _extract_page_text(html: str) -> str:
    parser = TextExtractor()
    parser.feed(html)
    return " ".join(parser.parts)


def _parse_result_page(html: str) -> JackpotPageDetails:
    text = _extract_page_text(html)

    jackpot_match = re.search(
        r"Match 5 and 2 Stars\s+"
        r"(£[\d,]+(?:\.\d+)?)\s+"
        r"([\d,]+)\s+"
        r"([\d,]+)\s+"
        r"(?:£[\d,]+(?:\.\d+)?|-)",
        text,
    )
    jackpot_prize_gbp = None
    uk_jackpot_winners = None
    total_jackpot_winners = None
    if jackpot_match:
        jackpot_prize_gbp = _money_to_float(jackpot_match.group(1))
        uk_jackpot_winners = _int_from_text(jackpot_match.group(2))
        total_jackpot_winners = _int_from_text(jackpot_match.group(3))

    rollover_match = re.search(r"It's a (\d+)x Rollover!", text)
    rollover_count = int(rollover_match.group(1)) if rollover_match else None

    ticket_info = ""
    ticket_match = re.search(
        r"Winning Ticket Information\s+(.*?)\s+Additional Draw Details",
        text,
    )
    if ticket_match:
        ticket_info = ticket_match.group(1).strip()

    ball_set_match = re.search(r"Ball Set Used:\s*(\d+)", text)
    machine_match = re.search(r"Ball Machine Used:\s*(\d+)", text)

    return JackpotPageDetails(
        jackpot_prize_gbp=jackpot_prize_gbp,
        uk_jackpot_winners=uk_jackpot_winners,
        total_jackpot_winners=total_jackpot_winners,
        rollover_count=rollover_count,
        winning_ticket_info=ticket_info,
        ball_set=int(ball_set_match.group(1)) if ball_set_match else None,
        ball_machine=int(machine_match.group(1)) if machine_match else None,
    )


def _fetch_html(url: str) -> str:
    request = Request(url, headers={"User-Agent": "MillionaireProject/1.0"})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def _load_or_fetch_page(date_value: pd.Timestamp, delay_seconds: float, refresh: bool) -> tuple[str, str]:
    date_slug = date_value.strftime("%d-%m-%Y")
    url = RESULT_URL.format(date_slug=date_slug)
    cache_path = HTML_CACHE_DIR / f"{date_slug}.html"

    if cache_path.exists() and not refresh:
        return cache_path.read_text(encoding="utf-8"), url

    html = _fetch_html(url)
    cache_path.write_text(html, encoding="utf-8")
    if delay_seconds:
        time.sleep(delay_seconds)
    return html, url


def build_jackpot_details(
    *,
    delay_seconds: float = 0.2,
    refresh: bool = False,
    limit: int | None = None,
) -> pd.DataFrame:
    OUTPUT_DIR.mkdir(exist_ok=True)
    HTML_CACHE_DIR.mkdir(exist_ok=True)

    draws = load_draws().dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)
    if limit is not None:
        draws = draws.tail(limit).reset_index(drop=True)

    rows: list[dict[str, object]] = []
    for index, row in draws.iterrows():
        draw_date = row["Date"]
        try:
            html, url = _load_or_fetch_page(draw_date, delay_seconds, refresh)
            details = _parse_result_page(html)
            fetch_error = ""
        except (HTTPError, URLError, TimeoutError, RuntimeError, ValueError) as error:
            url = RESULT_URL.format(date_slug=draw_date.strftime("%d-%m-%Y"))
            details = JackpotPageDetails(None, None, None, None, "", None, None)
            fetch_error = str(error)

        balls = sorted(row["Balls"])
        stars = sorted(row["LuckyStars"])
        total_jackpot_winners = details.total_jackpot_winners
        jackpot_won = bool(total_jackpot_winners and total_jackpot_winners > 0)

        rows.append(
            {
                "Date": draw_date.date().isoformat(),
                "Year": int(draw_date.year),
                "Month": draw_date.month_name(),
                "Month number": int(draw_date.month),
                "Quarter": f"Q{int(math.ceil(draw_date.month / 3))}",
                "Weekday": draw_date.day_name(),
                "Draw index": index + 1,
                "Balls": str(balls),
                "LuckyStars": str(stars),
                "Ball sum": sum(balls),
                "Low ball count": sum(number <= 25 for number in balls),
                "High ball count": sum(number > 25 for number in balls),
                "Odd ball count": sum(number % 2 == 1 for number in balls),
                "Even ball count": sum(number % 2 == 0 for number in balls),
                "Birthday ball count": sum(number <= 31 for number in balls),
                "Consecutive pairs": sum(
                    1 for first, second in zip(balls, balls[1:]) if second - first == 1
                ),
                "Star sum": sum(stars),
                "Jackpot prize GBP": details.jackpot_prize_gbp,
                "UK jackpot winners": details.uk_jackpot_winners,
                "Total jackpot winners": total_jackpot_winners,
                "Jackpot won": jackpot_won,
                "Rollover count": details.rollover_count,
                "Winning ticket information": details.winning_ticket_info,
                "Ball set": details.ball_set,
                "Ball machine": details.ball_machine,
                "Result URL": url,
                "Fetch error": fetch_error,
            }
        )

    details_df = pd.DataFrame(rows)
    details_df.to_csv(DETAILS_FILE, index=False)
    return details_df


def _rate_table(df: pd.DataFrame, group_column: str) -> pd.DataFrame:
    grouped = (
        df.groupby(group_column, dropna=False)
        .agg(draws=("Jackpot won", "size"), jackpot_wins=("Jackpot won", "sum"))
        .reset_index()
    )
    grouped["jackpot_win_rate"] = grouped["jackpot_wins"] / grouped["draws"]
    expected = df["Jackpot won"].mean()
    grouped["expected_wins_at_overall_rate"] = grouped["draws"] * expected
    grouped["lift_vs_overall_rate"] = grouped["jackpot_win_rate"] / expected
    return grouped


def summarize_jackpot_patterns(details_df: pd.DataFrame) -> pd.DataFrame:
    clean = details_df[details_df["Total jackpot winners"].notna()].copy()
    clean["Jackpot won"] = clean["Jackpot won"].astype(bool)

    summary_frames = []
    for dimension in ["Year", "Month", "Quarter", "Weekday", "Rollover count", "Ball set", "Ball machine"]:
        table = _rate_table(clean, dimension)
        table.insert(0, "Dimension", dimension)
        table = table.rename(columns={dimension: "Segment"})
        summary_frames.append(table)

    numeric_rows = []
    won = clean[clean["Jackpot won"]]
    not_won = clean[~clean["Jackpot won"]]
    for column in [
        "Jackpot prize GBP",
        "Ball sum",
        "Low ball count",
        "High ball count",
        "Odd ball count",
        "Even ball count",
        "Birthday ball count",
        "Consecutive pairs",
        "Star sum",
    ]:
        numeric_rows.append(
            {
                "Dimension": "Won vs not won numeric mean",
                "Segment": column,
                "draws": len(clean),
                "jackpot_wins": int(clean["Jackpot won"].sum()),
                "jackpot_win_rate": clean["Jackpot won"].mean(),
                "expected_wins_at_overall_rate": None,
                "lift_vs_overall_rate": None,
                "won_mean": won[column].mean(),
                "not_won_mean": not_won[column].mean(),
                "difference": won[column].mean() - not_won[column].mean(),
            }
        )

    summary = pd.concat(summary_frames + [pd.DataFrame(numeric_rows)], ignore_index=True)
    summary.to_csv(SUMMARY_FILE, index=False)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Deep-dive into when EuroMillions jackpots are won.")
    parser.add_argument("--delay", type=float, default=0.2, help="Delay between uncached result-page requests.")
    parser.add_argument("--refresh", action="store_true", help="Refetch pages even when cached HTML exists.")
    parser.add_argument("--limit", type=int, default=None, help="Analyze only the latest N draws.")
    args = parser.parse_args()

    details = build_jackpot_details(delay_seconds=args.delay, refresh=args.refresh, limit=args.limit)
    summary = summarize_jackpot_patterns(details)

    parsed = details["Total jackpot winners"].notna().sum()
    wins = int(details["Jackpot won"].sum())
    print(f"Wrote {DETAILS_FILE} with {len(details)} rows; parsed jackpot winner counts for {parsed} rows.")
    print(f"Observed {wins} jackpot-winning draws.")
    print(f"Wrote {SUMMARY_FILE} with {len(summary)} summary rows.")


if __name__ == "__main__":
    main()
