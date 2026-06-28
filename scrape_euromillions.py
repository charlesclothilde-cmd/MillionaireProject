#!/usr/bin/env python

from __future__ import annotations

import argparse
import re
import time
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd

from lottery_data import DATA_FILE, save_draws, validate_draws


ARCHIVE_URL = "https://www.lottery.co.uk/euromillions/results/archive-{year}"
ORDINAL_SUFFIX_RE = re.compile(r"\b(\d{1,2})(st|nd|rd|th)\b")


class EuroMillionsArchiveParser(HTMLParser):
    """Extract draw rows from a lottery.co.uk EuroMillions archive page.

    The archive is server-rendered HTML, so the standard library HTMLParser is
    enough here. Each useful table row contains one date link, five main number
    divs, and two Lucky Star divs. Rows that do not match that shape are ignored.
    """

    def __init__(self) -> None:
        super().__init__()
        self.draws: list[dict[str, object]] = []
        self._in_row = False
        self._in_date_link = False
        self._number_kind: str | None = None
        self._date_text: list[str] = []
        self._balls: list[int] = []
        self._stars: list[int] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        classes = set((attr_map.get("class") or "").split())

        # Every draw sits inside a table row. Reset temporary state at the start
        # of each row so unrelated page content cannot leak into the next draw.
        if tag == "tr":
            self._in_row = True
            self._date_text = []
            self._balls = []
            self._stars = []

        if not self._in_row:
            return

        # Draw date links look like /euromillions/results-31-12-2024 and their
        # visible text is a human date, e.g. "Tuesday 31st Dec 2024".
        if tag == "a" and (attr_map.get("href") or "").startswith("/euromillions/results-"):
            self._in_date_link = True

        # The page uses different CSS classes for the five main balls and the
        # two Lucky Stars. Track which kind of number the next text belongs to.
        if tag == "div" and "result" in classes:
            if "euromillions-ball" in classes:
                self._number_kind = "ball"
            elif "euromillions-lucky-star" in classes:
                self._number_kind = "star"

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return

        if self._in_date_link:
            self._date_text.append(text)
        elif self._number_kind:
            number = int(text)
            if self._number_kind == "ball":
                self._balls.append(number)
            else:
                self._stars.append(number)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            self._in_date_link = False
        elif tag == "div":
            self._number_kind = None
        elif tag == "tr" and self._in_row:
            self._finish_row()
            self._in_row = False

    def _finish_row(self) -> None:
        if not self._date_text or len(self._balls) != 5 or len(self._stars) != 2:
            return

        # Pandas cannot parse ordinal suffixes with a strict format, so convert
        # "31st" -> "31", "2nd" -> "2", etc. before parsing the draw date.
        date_text = ORDINAL_SUFFIX_RE.sub(r"\1", " ".join(self._date_text))
        draw_date = pd.to_datetime(date_text, format="%A %d %b %Y", errors="coerce")
        if pd.isna(draw_date):
            draw_date = pd.to_datetime(date_text, errors="coerce")
        if pd.isna(draw_date):
            raise ValueError(f"Could not parse draw date: {' '.join(self._date_text)}")

        self.draws.append(
            {
                "Date": draw_date,
                "Year": draw_date.year,
                "Balls": sorted(self._balls),
                "LuckyStars": sorted(self._stars),
            }
        )


def fetch_archive_year(year: int) -> pd.DataFrame:
    """Download and parse one archive year into the project CSV schema."""
    url = ARCHIVE_URL.format(year=year)
    request = Request(url, headers={"User-Agent": "MillionaireProject/1.0"})

    try:
        with urlopen(request, timeout=30) as response:
            html = response.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError) as error:
        raise RuntimeError(f"Could not fetch {url}: {error}") from error

    parser = EuroMillionsArchiveParser()
    parser.feed(html)
    if not parser.draws:
        raise RuntimeError(f"No EuroMillions draws found at {url}")

    return pd.DataFrame(parser.draws)


def scrape_archives(start_year: int, end_year: int, *, delay_seconds: float = 0.25) -> pd.DataFrame:
    """Fetch all requested years, de-duplicate by date, and validate numbers."""
    frames = []
    for year in range(start_year, end_year + 1):
        print(f"Fetching {year}...")
        frames.append(fetch_archive_year(year))
        if delay_seconds:
            time.sleep(delay_seconds)

    draws = pd.concat(frames, ignore_index=True)
    # Re-running the scraper is safe: if a year page overlaps or is fetched
    # again, the same draw date is kept only once.
    draws = draws.drop_duplicates(subset=["Date"]).sort_values("Date").reset_index(drop=True)
    validate_draws(draws)
    return draws


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape EuroMillions archive pages and write a dated master CSV."
    )
    parser.add_argument("--start-year", type=int, default=2004)
    parser.add_argument("--end-year", type=int, default=date.today().year)
    parser.add_argument("--output", type=Path, default=DATA_FILE)
    parser.add_argument("--delay", type=float, default=0.25, help="Delay between year requests in seconds.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and validate without writing the CSV.")
    args = parser.parse_args()

    draws = scrape_archives(args.start_year, args.end_year, delay_seconds=args.delay)
    print(f"Fetched {len(draws)} draws from {draws['Date'].min().date()} through {draws['Date'].max().date()}.")

    if args.dry_run:
        return

    save_draws(draws, args.output)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
