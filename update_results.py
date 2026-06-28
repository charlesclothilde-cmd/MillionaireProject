#!/usr/bin/env python

import argparse
from pathlib import Path

from lottery_data import DATA_FILE, append_new_draws, load_draws


def main() -> None:
    parser = argparse.ArgumentParser(description="Append validated EuroMillions draws to the master CSV.")
    parser.add_argument(
        "new_draws",
        type=Path,
        help="CSV containing Date, Balls, and LuckyStars columns for new official draws.",
    )
    parser.add_argument(
        "--data-file",
        type=Path,
        default=DATA_FILE,
        help=f"Master draw CSV to update. Defaults to {DATA_FILE}.",
    )
    args = parser.parse_args()

    before = load_draws(args.data_file)
    added = append_new_draws(args.data_file, args.new_draws)
    after = load_draws(args.data_file)

    print(f"Existing rows: {len(before)}")
    print(f"Added rows: {added}")
    print(f"Total rows: {len(after)}")


if __name__ == "__main__":
    main()
